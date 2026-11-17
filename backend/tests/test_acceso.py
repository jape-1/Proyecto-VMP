"""Flujo del guardia: QR -> captura -> IA -> decisión (HU07–HU12, docs/18 §7)."""

from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.enums import EstadoQR, EstadoValidacion
from app.core.time import ahora
from app.ia.cliente import ErrorIA
from app.modules.estacionamiento.models import (
    EventoDeteccionIA,
    IntentoLecturaQR,
    SesionEstacionamiento,
)
from app.modules.identidad.models import CodigoQR
from tests.conftest import API, imagen_png


def _leer_qr(cliente: TestClient, cabeceras: dict, token: str) -> dict:
    respuesta = cliente.post(f"{API}/acceso/qr", json={"token": token}, headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _capturar(cliente: TestClient, cabeceras: dict, id_sesion: int, nombre: str = "scooter.png"):
    respuesta = cliente.post(
        f"{API}/acceso/{id_sesion}/captura",
        files={"archivo": (nombre, imagen_png(), "image/png")},
        headers=cabeceras,
    )
    assert respuesta.status_code == 202, respuesta.text
    return respuesta.json()


def test_flujo_feliz_validado(
    cliente: TestClient,
    preparar_usuario,
    token_guardia,
    token_qr,
    db: Session,
):
    _, ids = preparar_usuario(vehiculos=({"tipo_vmp": "scooter_electrico"},))
    guardia = token_guardia()

    lectura = _leer_qr(cliente, guardia, token_qr())
    assert lectura["siguiente_paso"] == "capturar_foto"
    assert lectura["usuario"]["codigo_utp"] == "U90000001"
    assert len(lectura["vehiculos"]) == 1
    assert lectura["vehiculos"][0]["foto_referencia_url"]

    id_sesion = lectura["id_sesion"]
    captura = _capturar(cliente, guardia, id_sesion)
    assert captura["estado"] == "pendiente"

    estado = cliente.get(f"{API}/acceso/{id_sesion}", headers=guardia).json()
    assert estado["estado"] == "validado"
    assert estado["id_vehiculo_reconocido"] == ids[0]
    assert estado["confianza"] == 0.9
    assert estado["detecciones"][0]["clase"] == "scooter"
    assert estado["modelo_version"] == "stub-v1"
    assert estado["puede_decidir"] is False
    assert estado["evidencia_url"].startswith(f"{API}/archivos/capturas/")

    # La evidencia quedó registrada.
    evento = db.scalar(select(EventoDeteccionIA))
    assert evento is not None
    assert evento.modelo_version == "stub-v1"
    assert evento.motivo is None


def test_no_coincide_y_decision_manual(
    cliente: TestClient, preparar_usuario, token_guardia, token_qr, db: Session
):
    # El usuario solo tiene una bicicleta; la captura muestra un scooter.
    _, ids = preparar_usuario(
        vehiculos=({"tipo_vmp": "bicicleta", "marca": "Trek", "archivo": "bicicleta.png"},)
    )
    guardia = token_guardia()
    id_sesion = _leer_qr(cliente, guardia, token_qr())["id_sesion"]
    _capturar(cliente, guardia, id_sesion, "scooter.png")

    estado = cliente.get(f"{API}/acceso/{id_sesion}", headers=guardia).json()
    assert estado["estado"] == "rechazado"
    assert estado["motivo"] == "VEHICULO_NO_COINCIDE"
    assert estado["puede_decidir"] is True
    # La IA no asigna vehículo cuando no coincide.
    assert estado["id_vehiculo_reconocido"] is None

    decision = cliente.post(
        f"{API}/acceso/{id_sesion}/decision",
        json={"decision": "aprobar_manual", "id_vehiculo": ids[0], "motivo": "Es su bici"},
        headers=guardia,
    )
    assert decision.status_code == 200, decision.text
    cuerpo = decision.json()
    assert cuerpo["estado"] == "validado"
    assert cuerpo["decision"]["decision"] == "aprobar_manual"
    assert cuerpo["decision"]["motivo"] == "Es su bici"

    sesion = db.get(SesionEstacionamiento, id_sesion)
    db.refresh(sesion)
    assert sesion.estado_validacion == EstadoValidacion.validado
    assert sesion.id_personal_decision is not None


def test_rechazo_manual_queda_registrado(
    cliente: TestClient, preparar_usuario, token_guardia, token_qr, db: Session
):
    preparar_usuario(vehiculos=({"tipo_vmp": "scooter_electrico"},))
    guardia = token_guardia()
    id_sesion = _leer_qr(cliente, guardia, token_qr())["id_sesion"]
    _capturar(cliente, guardia, id_sesion, "vacio.png")  # sin detección -> verificar

    estado = cliente.get(f"{API}/acceso/{id_sesion}", headers=guardia).json()
    assert estado["estado"] == "verificar"

    decision = cliente.post(
        f"{API}/acceso/{id_sesion}/decision",
        json={"decision": "rechazar", "motivo": "No es el vehículo del usuario"},
        headers=guardia,
    )
    assert decision.status_code == 200, decision.text
    assert decision.json()["estado"] == "rechazado"
    assert decision.json()["motivo"] == "RECHAZADO_MANUAL"

    sesion = db.get(SesionEstacionamiento, id_sesion)
    db.refresh(sesion)
    assert sesion.estado_sesion.value == "con_incidencia"


def test_ia_caida_permite_decision_manual(
    cliente: TestClient, preparar_usuario, token_guardia, token_qr, monkeypatch
):
    preparar_usuario(vehiculos=({"tipo_vmp": "scooter_electrico"},))
    guardia = token_guardia()

    class _IARota:
        def validar_ingreso(self, *_, **__):
            raise ErrorIA("sin conexión")

        def validar_foto_referencia(self, *_, **__):
            raise ErrorIA("sin conexión")

        def salud(self):
            return {"disponible": False}

    monkeypatch.setattr("app.modules.estacionamiento.service.obtener_cliente_ia", lambda: _IARota())

    id_sesion = _leer_qr(cliente, guardia, token_qr())["id_sesion"]
    _capturar(cliente, guardia, id_sesion)

    estado = cliente.get(f"{API}/acceso/{id_sesion}", headers=guardia).json()
    assert estado["estado"] == "ia_no_disponible"
    assert estado["motivo"] == "IA_NO_DISPONIBLE"
    assert estado["puede_decidir"] is True

    decision = cliente.post(
        f"{API}/acceso/{id_sesion}/decision",
        json={"decision": "aprobar_manual", "motivo": "IA caída, verificado a ojo"},
        headers=guardia,
    )
    assert decision.status_code == 200, decision.text
    assert decision.json()["estado"] == "validado"


def test_qr_alterado_se_registra(cliente: TestClient, token_guardia, db: Session):
    guardia = token_guardia()
    respuesta = cliente.post(f"{API}/acceso/qr", json={"token": "vmp1_corto"}, headers=guardia)
    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == "QR_ALTERADO"

    intentos = db.scalar(select(func.count()).select_from(IntentoLecturaQR))
    assert intentos == 1


def test_qr_inexistente(cliente: TestClient, token_guardia):
    guardia = token_guardia()
    token = "vmp1_" + "a" * 43
    respuesta = cliente.post(f"{API}/acceso/qr", json={"token": token}, headers=guardia)
    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "QR_INEXISTENTE"


def test_qr_vencido_y_revocado(
    cliente: TestClient, preparar_usuario, token_guardia, token_qr, db: Session
):
    preparar_usuario(vehiculos=({"archivo": "scooter.png"},))
    guardia = token_guardia()
    token = token_qr()

    db.execute(
        update(CodigoQR).values(
            fecha_expiracion=ahora().replace(year=2020),
            fecha_generacion=ahora().replace(year=2019),
        )
    )
    db.commit()
    vencido = cliente.post(f"{API}/acceso/qr", json={"token": token}, headers=guardia)
    assert vencido.status_code == 409
    assert vencido.json()["codigo"] == "QR_EXPIRADO"

    db.execute(update(CodigoQR).values(estado=EstadoQR.revocado))
    db.commit()
    revocado = cliente.post(f"{API}/acceso/qr", json={"token": token}, headers=guardia)
    assert revocado.status_code == 409
    assert revocado.json()["codigo"] == "QR_REVOCADO"


def test_usuario_sin_vehiculos_no_abre_sesion(
    cliente: TestClient, preparar_usuario, token_guardia, token_qr, db: Session
):
    preparar_usuario()  # consentimiento, sin vehículos
    guardia = token_guardia()
    respuesta = cliente.post(f"{API}/acceso/qr", json={"token": token_qr()}, headers=guardia)
    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "SIN_VEHICULOS_REGISTRADOS"

    # HU18: los intentos fallidos también se registran.
    intento = db.scalar(select(IntentoLecturaQR))
    assert intento is not None
    assert intento.motivo == "SIN_VEHICULOS_REGISTRADOS"


def test_matricula_inactiva_bloquea_el_ingreso(
    cliente: TestClient, preparar_usuario, token_guardia, token_qr
):
    preparar_usuario("U90000006", vehiculos=({"archivo": "scooter.png"},))
    guardia = token_guardia()
    respuesta = cliente.post(
        f"{API}/acceso/qr", json={"token": token_qr("U90000006")}, headers=guardia
    )
    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "USUARIO_INACTIVO"


def test_vehiculo_dentro_no_se_puede_dar_de_baja(
    cliente: TestClient, preparar_usuario, token_guardia, token_qr
):
    cabeceras, ids = preparar_usuario(vehiculos=({"archivo": "scooter.png"},))
    guardia = token_guardia()
    id_sesion = _leer_qr(cliente, guardia, token_qr())["id_sesion"]
    _capturar(cliente, guardia, id_sesion)

    respuesta = cliente.delete(f"{API}/usuarios/me/vehiculos/{ids[0]}", headers=cabeceras)
    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "VEHICULO_DENTRO_NO_ELIMINABLE"


def test_cancelar_ingreso(cliente: TestClient, preparar_usuario, token_guardia, token_qr):
    preparar_usuario(vehiculos=({"archivo": "scooter.png"},))
    guardia = token_guardia()
    id_sesion = _leer_qr(cliente, guardia, token_qr())["id_sesion"]

    respuesta = cliente.post(f"{API}/acceso/{id_sesion}/cancelar", headers=guardia)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["motivo"] == "CANCELADO"

    # Una sesión cancelada no admite captura.
    captura = cliente.post(
        f"{API}/acceso/{id_sesion}/captura",
        files={"archivo": ("scooter.png", imagen_png(), "image/png")},
        headers=guardia,
    )
    assert captura.status_code == 409


def test_stream_sse_entrega_el_estado(
    cliente: TestClient, preparar_usuario, token_guardia, token_qr
):
    preparar_usuario(vehiculos=({"archivo": "scooter.png"},))
    guardia = token_guardia()
    id_sesion = _leer_qr(cliente, guardia, token_qr())["id_sesion"]
    _capturar(cliente, guardia, id_sesion)

    token = guardia["Authorization"].removeprefix("Bearer ")
    with cliente.stream("GET", f"{API}/acceso/{id_sesion}/stream?token={token}") as respuesta:
        assert respuesta.status_code == 200
        assert respuesta.headers["content-type"].startswith("text/event-stream")
        texto = "".join(respuesta.iter_text())

    assert "event: estado" in texto
    assert '"estado":"validado"' in texto.replace(" ", "")


def test_puede_decidir_solo_en_estados_manuales(
    cliente: TestClient, preparar_usuario, token_guardia, token_qr
):
    preparar_usuario(vehiculos=({"archivo": "scooter.png"},))
    guardia = token_guardia()
    id_sesion = _leer_qr(cliente, guardia, token_qr())["id_sesion"]
    _capturar(cliente, guardia, id_sesion)

    respuesta = cliente.post(
        f"{API}/acceso/{id_sesion}/decision",
        json={"decision": "rechazar"},
        headers=guardia,
    )
    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "SESION_ESTADO_INVALIDO"


def test_moto_electrica_registrada_se_valida(
    cliente: TestClient, preparar_usuario, token_guardia, token_qr
):
    # El detector tiene 3 clases desde el 16-nov (docs/13 §F): la moto ya no va siempre a mano.
    _, ids = preparar_usuario(
        vehiculos=({"tipo_vmp": "moto_electrica", "marca": "Niu", "archivo": "moto.png"},)
    )
    guardia = token_guardia()
    id_sesion = _leer_qr(cliente, guardia, token_qr())["id_sesion"]
    _capturar(cliente, guardia, id_sesion, "moto.png")

    estado = cliente.get(f"{API}/acceso/{id_sesion}", headers=guardia).json()
    assert estado["estado"] == "validado"
    assert estado["detecciones"][0]["clase"] == "moto_electrica"
    assert estado["id_vehiculo_reconocido"] == ids[0]


def test_moto_no_coincide_con_scooter_registrado(
    cliente: TestClient, preparar_usuario, token_guardia, token_qr
):
    preparar_usuario(vehiculos=({"tipo_vmp": "scooter_electrico"},))
    guardia = token_guardia()
    id_sesion = _leer_qr(cliente, guardia, token_qr())["id_sesion"]
    _capturar(cliente, guardia, id_sesion, "moto.png")

    estado = cliente.get(f"{API}/acceso/{id_sesion}", headers=guardia).json()
    assert estado["estado"] == "rechazado"
    assert estado["motivo"] == "VEHICULO_NO_COINCIDE"


def test_rechazo_manual_es_definitivo(
    cliente: TestClient, preparar_usuario, token_guardia, token_qr
):
    preparar_usuario(vehiculos=({"tipo_vmp": "scooter_electrico"},))
    guardia = token_guardia()
    id_sesion = _leer_qr(cliente, guardia, token_qr())["id_sesion"]
    _capturar(cliente, guardia, id_sesion, "vacio.png")  # verificar

    rechazo = cliente.post(
        f"{API}/acceso/{id_sesion}/decision",
        json={"decision": "rechazar", "motivo": "No es su vehículo"},
        headers=guardia,
    )
    assert rechazo.status_code == 200, rechazo.text
    assert rechazo.json()["puede_decidir"] is False

    # Ni el mismo guardia ni otro pueden aprobar después.
    otro = token_guardia("admin.seguridad")
    aprobar = cliente.post(
        f"{API}/acceso/{id_sesion}/decision",
        json={"decision": "aprobar_manual", "motivo": "Cambio de opinión"},
        headers=otro,
    )
    assert aprobar.status_code == 409
    assert aprobar.json()["codigo"] == "SESION_ESTADO_INVALIDO"

    # Tampoco se admite otra captura ni cancelar: hay que leer el QR de nuevo.
    captura = cliente.post(
        f"{API}/acceso/{id_sesion}/captura",
        files={"archivo": ("scooter.png", imagen_png(), "image/png")},
        headers=guardia,
    )
    assert captura.status_code == 409
    cancelar = cliente.post(f"{API}/acceso/{id_sesion}/cancelar", headers=guardia)
    assert cancelar.status_code == 409

    estado = cliente.get(f"{API}/acceso/{id_sesion}", headers=guardia).json()
    assert estado["estado"] == "rechazado"
    assert estado["motivo"] == "RECHAZADO_MANUAL"


def test_cancelar_mientras_la_ia_analiza_no_revive_la_sesion(
    cliente: TestClient, preparar_usuario, token_guardia, token_qr, db: Session, monkeypatch
):
    from app.core.db import SessionLocal
    from app.ia.cliente import ClienteIAStub
    from app.modules.estacionamiento import service

    preparar_usuario(vehiculos=({"tipo_vmp": "scooter_electrico"},))
    guardia = token_guardia()
    id_sesion = _leer_qr(cliente, guardia, token_qr())["id_sesion"]

    class _IALenta(ClienteIAStub):
        """Mientras «analiza», el guardia cancela desde otra conexión."""

        def validar_ingreso(self, *args, **kwargs):
            otra = SessionLocal()
            try:
                service.cancelar(otra, id_sesion)
            finally:
                otra.close()
            return super().validar_ingreso(*args, **kwargs)

    monkeypatch.setattr(
        "app.modules.estacionamiento.service.obtener_cliente_ia", lambda: _IALenta()
    )
    _capturar(cliente, guardia, id_sesion, "scooter.png")

    estado = cliente.get(f"{API}/acceso/{id_sesion}", headers=guardia).json()
    assert estado["estado"] != "validado"
    assert estado["motivo"] == "CANCELADO"
    assert estado["puede_decidir"] is False
    assert estado["id_vehiculo_reconocido"] is None

    # El resultado de la IA igual queda como evidencia.
    assert db.scalar(select(func.count()).select_from(EventoDeteccionIA)) == 1


def test_vehiculo_que_ya_esta_dentro_va_a_verificar(
    cliente: TestClient, preparar_usuario, token_guardia, token_qr, db: Session
):
    """Sin registro de salida en este avance, un segundo ingreso no debe tumbar la IA."""
    preparar_usuario(vehiculos=({"tipo_vmp": "scooter_electrico"},))
    guardia = token_guardia()

    primera = _leer_qr(cliente, guardia, token_qr())["id_sesion"]
    _capturar(cliente, guardia, primera)
    assert cliente.get(f"{API}/acceso/{primera}", headers=guardia).json()["estado"] == "validado"

    segunda = _leer_qr(cliente, guardia, token_qr())["id_sesion"]
    _capturar(cliente, guardia, segunda)
    estado = cliente.get(f"{API}/acceso/{segunda}", headers=guardia).json()
    assert estado["estado"] == "verificar"
    assert estado["motivo"] == "VEHICULO_YA_DENTRO"
    assert estado["id_vehiculo_reconocido"] is None
    assert estado["puede_decidir"] is True

    # La evidencia del segundo intento también queda guardada.
    assert db.scalar(select(func.count()).select_from(EventoDeteccionIA)) == 2


def test_salida_de_demo_permite_volver_a_ingresar(
    cliente: TestClient, preparar_usuario, token_guardia, token_qr, db: Session
):
    """Ruta solo de desarrollo: este avance no registra salidas (docs/18 §2)."""
    _, ids = preparar_usuario(vehiculos=({"tipo_vmp": "scooter_electrico"},))
    guardia = token_guardia()

    primera = _leer_qr(cliente, guardia, token_qr())["id_sesion"]
    _capturar(cliente, guardia, primera)

    salida = cliente.post(f"{API}/dev/salida/U90000001")
    assert salida.status_code == 200, salida.text
    assert salida.json() == {"codigo_utp": "U90000001", "salidas_registradas": 1}

    sesion = db.get(SesionEstacionamiento, primera)
    db.refresh(sesion)
    assert sesion.fecha_hora_salida is not None
    assert sesion.estado_sesion.value == "finalizada"

    # El mismo vehículo vuelve a validarse solo.
    segunda = _leer_qr(cliente, guardia, token_qr())["id_sesion"]
    _capturar(cliente, guardia, segunda)
    estado = cliente.get(f"{API}/acceso/{segunda}", headers=guardia).json()
    assert estado["estado"] == "validado"
    assert estado["id_vehiculo_reconocido"] == ids[0]

    # Sin ingresos vigentes no hay nada que cerrar... salvo el que se acaba de validar.
    assert cliente.post(f"{API}/dev/salida/U90000001").json()["salidas_registradas"] == 1
    assert cliente.post(f"{API}/dev/salida/U90000001").json()["salidas_registradas"] == 0


def _cuadro(cliente: TestClient, cabeceras: dict, id_sesion: int, nombre: str = "scooter.png"):
    return cliente.post(
        f"{API}/acceso/{id_sesion}/cuadro",
        files={"archivo": (nombre, imagen_png(), "image/png")},
        headers=cabeceras,
    )


def test_cuadro_en_vivo_analiza_sin_guardar(
    cliente: TestClient, preparar_usuario, token_guardia, token_qr, db: Session
):
    """El video en vivo pregunta varias veces por segundo: nada de eso es evidencia."""
    _, ids = preparar_usuario(vehiculos=({"tipo_vmp": "scooter_electrico"},))
    guardia = token_guardia()
    id_sesion = _leer_qr(cliente, guardia, token_qr())["id_sesion"]

    respuesta = _cuadro(cliente, guardia, id_sesion)
    assert respuesta.status_code == 200, respuesta.text
    cuadro = respuesta.json()
    assert cuadro["estado"] == "validado"
    assert cuadro["id_vehiculo_mas_parecido"] == ids[0]
    assert cuadro["semejanza"] == 0.85
    assert cuadro["detecciones"][0]["clase"] == "scooter"
    assert cuadro["detecciones"][0]["caja"] == [0.31, 0.22, 0.62, 0.78]
    assert cuadro["umbral_semejanza"] == 0.70

    # Nada guardado y la sesión sigue esperando.
    assert db.scalar(select(func.count()).select_from(EventoDeteccionIA)) == 0
    estado = cliente.get(f"{API}/acceso/{id_sesion}", headers=guardia).json()
    assert estado["estado"] == "pendiente"

    # Otro vehículo: el cuadro lo dice, pero tampoco decide nada.
    distinto = _cuadro(cliente, guardia, id_sesion, "scooter-distinto.png").json()
    assert distinto["estado"] == "verificar"
    assert distinto["motivo"] == "SEMEJANZA_BAJA"

    # La decisión oficial llega con /captura y deja evidencia.
    _capturar(cliente, guardia, id_sesion)
    assert cliente.get(f"{API}/acceso/{id_sesion}", headers=guardia).json()["estado"] == "validado"
    assert db.scalar(select(func.count()).select_from(EventoDeteccionIA)) == 1

    # Con la sesión ya validada no se analizan más cuadros.
    assert _cuadro(cliente, guardia, id_sesion).status_code == 409


def test_cuadro_con_ia_caida_responde_503(
    cliente: TestClient, preparar_usuario, token_guardia, token_qr, monkeypatch
):
    preparar_usuario(vehiculos=({"tipo_vmp": "scooter_electrico"},))
    guardia = token_guardia()
    id_sesion = _leer_qr(cliente, guardia, token_qr())["id_sesion"]

    class _IARota:
        def validar_ingreso(self, *_, **__):
            raise ErrorIA("sin conexión")

    monkeypatch.setattr("app.modules.estacionamiento.service.obtener_cliente_ia", lambda: _IARota())
    respuesta = _cuadro(cliente, guardia, id_sesion)
    assert respuesta.status_code == 503
    assert respuesta.json()["codigo"] == "IA_NO_DISPONIBLE"


def test_cuadro_exige_guardia(cliente: TestClient, preparar_usuario, token_guardia, token_qr):
    cabeceras_usuario, _ = preparar_usuario(vehiculos=({"tipo_vmp": "scooter_electrico"},))
    id_sesion = _leer_qr(cliente, token_guardia(), token_qr())["id_sesion"]
    assert _cuadro(cliente, cabeceras_usuario, id_sesion).status_code in (401, 403)
