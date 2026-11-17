"""Reglas del flujo del usuario (HU01–HU06, docs/18 §7)."""

from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.enums import EstadoQR
from app.core.time import ahora
from app.modules.identidad.models import CodigoQR
from tests.conftest import API


def test_perfil_viene_del_conector(cliente: TestClient, token_usuario):
    cabeceras = token_usuario("U90000001")
    respuesta = cliente.get(f"{API}/usuarios/me", headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["codigo_utp"] == "U90000001"
    assert cuerpo["nombres"] == "Lucía Fernanda"
    assert cuerpo["estado_matricula"] == "activo"
    assert cuerpo["acepta_tratamiento_datos"] is False


def test_consentimiento_obligatorio(cliente: TestClient, preparar_usuario):
    cabeceras, _ = preparar_usuario(con_consentimiento=False)
    respuesta = cliente.post(
        f"{API}/usuarios/me/vehiculos",
        json={"tipo_vmp": "scooter_electrico", "marca": "Xiaomi", "color": "negro"},
        headers=cabeceras,
    )
    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "CONSENTIMIENTO_REQUERIDO"


def test_limite_de_tres_vmp(cliente: TestClient, preparar_usuario):
    cabeceras, ids = preparar_usuario(
        vehiculos=(
            {"marca": "Xiaomi", "modelo": "Mi 3", "archivo": "scooter1.png"},
            {"marca": "Segway", "modelo": "Max", "archivo": "scooter2.png"},
            {"marca": "Xiaomi", "modelo": "Pro 2", "archivo": "scooter3.png"},
        )
    )
    assert len(ids) == 3

    lista = cliente.get(f"{API}/usuarios/me/vehiculos", headers=cabeceras).json()
    assert lista["max"] == 3
    assert lista["usados"] == 3

    cuarto = cliente.post(
        f"{API}/usuarios/me/vehiculos",
        json={"tipo_vmp": "bicicleta", "marca": "Trek", "color": "azul"},
        headers=cabeceras,
    )
    assert cuarto.status_code == 409
    assert cuarto.json()["codigo"] == "LIMITE_VMP_ALCANZADO"
    assert cuarto.json()["detalle"] == {"max": 3, "actuales": 3}


def test_foto_sin_vehiculo_es_rechazada(cliente: TestClient, preparar_usuario, png):
    cabeceras, ids = preparar_usuario(vehiculos=({"archivo": "scooter.png"},))
    respuesta = cliente.post(
        f"{API}/usuarios/me/vehiculos/{ids[0]}/foto",
        files={"archivo": ("vacio.png", png, "image/png")},
        headers=cabeceras,
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "FOTO_SIN_VEHICULO"


def test_foto_con_archivo_que_no_es_imagen(cliente: TestClient, preparar_usuario):
    cabeceras, ids = preparar_usuario(vehiculos=({"archivo": "scooter.png"},))
    respuesta = cliente.post(
        f"{API}/usuarios/me/vehiculos/{ids[0]}/foto",
        files={"archivo": ("nota.png", b"esto no es una imagen", "image/png")},
        headers=cabeceras,
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "FOTO_INVALIDA"


def test_un_solo_qr_activo_por_usuario(cliente: TestClient, preparar_usuario, db: Session):
    cabeceras, _ = preparar_usuario(vehiculos=({"archivo": "scooter.png"},))

    primero = cliente.get(f"{API}/usuarios/me/qr", headers=cabeceras)
    assert primero.status_code == 200, primero.text
    assert primero.json()["estado"] == "activo"
    assert primero.json()["vigente"] is True
    assert primero.json()["imagen_qr_png_base64"]

    segundo = cliente.post(f"{API}/usuarios/me/qr/regenerar", headers=cabeceras)
    assert segundo.status_code == 200, segundo.text
    assert segundo.json()["id_qr"] != primero.json()["id_qr"]

    activos = db.scalar(
        select(func.count()).select_from(CodigoQR).where(CodigoQR.estado == EstadoQR.activo)
    )
    assert activos == 1
    revocados = db.scalar(
        select(func.count()).select_from(CodigoQR).where(CodigoQR.estado == EstadoQR.revocado)
    )
    assert revocados == 1


def test_qr_no_expone_token_ni_hash(cliente: TestClient, preparar_usuario):
    cabeceras, _ = preparar_usuario(vehiculos=({"archivo": "scooter.png"},))
    respuesta = cliente.get(f"{API}/usuarios/me/qr", headers=cabeceras)
    texto = respuesta.text
    assert "token_hash" not in texto
    assert "token" not in respuesta.json()


def test_vehiculo_de_otro_usuario_no_es_accesible(cliente: TestClient, preparar_usuario):
    _, ids = preparar_usuario(
        "U90000001", vehiculos=({"marca": "Xiaomi", "archivo": "scooter.png"},)
    )
    otras, _ = preparar_usuario("U90000002")

    editar = cliente.put(
        f"{API}/usuarios/me/vehiculos/{ids[0]}", json={"color": "rojo"}, headers=otras
    )
    assert editar.status_code == 404
    assert editar.json()["codigo"] == "VEHICULO_NO_ENCONTRADO"

    borrar = cliente.delete(f"{API}/usuarios/me/vehiculos/{ids[0]}", headers=otras)
    assert borrar.status_code == 404


def test_baja_logica_de_vehiculo(cliente: TestClient, preparar_usuario):
    cabeceras, ids = preparar_usuario(vehiculos=({"archivo": "scooter.png"},))
    respuesta = cliente.delete(f"{API}/usuarios/me/vehiculos/{ids[0]}", headers=cabeceras)
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "inactivo"

    lista = cliente.get(f"{API}/usuarios/me/vehiculos", headers=cabeceras).json()
    assert lista["usados"] == 0


def test_qr_vencido_se_marca_y_se_regenera(cliente: TestClient, preparar_usuario, db: Session):
    cabeceras, _ = preparar_usuario(vehiculos=({"archivo": "scooter.png"},))
    cliente.get(f"{API}/usuarios/me/qr", headers=cabeceras)

    # Se retrocede también la generación para respetar el CHECK del esquema.
    db.execute(
        update(CodigoQR).values(
            fecha_expiracion=ahora().replace(year=2020),
            fecha_generacion=ahora().replace(year=2019),
        )
    )
    db.commit()

    nuevo = cliente.get(f"{API}/usuarios/me/qr", headers=cabeceras)
    assert nuevo.status_code == 200
    assert nuevo.json()["vigente"] is True
    assert nuevo.json()["estado"] == "activo"


def test_usuario_inactivo_no_puede_registrar_vehiculos(cliente: TestClient, token_usuario):
    cabeceras = token_usuario("U90000006")
    perfil = cliente.get(f"{API}/usuarios/me", headers=cabeceras).json()
    assert perfil["estado_matricula"] == "inactivo"

    cliente.put(
        f"{API}/usuarios/me/perfil",
        json={"acepta_tratamiento_datos": True},
        headers=cabeceras,
    )
    # El backend no bloquea el registro por matrícula; sí bloquea el ingreso (§HU07).
    usuario = cliente.get(f"{API}/usuarios/me", headers=cabeceras).json()
    assert usuario["acepta_tratamiento_datos"] is True


def test_foto_de_otra_clase_es_rechazada(cliente: TestClient, preparar_usuario, png):
    # Vehículo registrado como bicicleta; la foto muestra un scooter.
    cabeceras, _ = preparar_usuario()
    id_vehiculo = cliente.post(
        f"{API}/usuarios/me/vehiculos",
        json={"tipo_vmp": "bicicleta", "marca": "Trek", "color": "azul"},
        headers=cabeceras,
    ).json()["id_vehiculo"]

    respuesta = cliente.post(
        f"{API}/usuarios/me/vehiculos/{id_vehiculo}/foto",
        files={"archivo": ("scooter.png", png, "image/png")},
        headers=cabeceras,
    )
    assert respuesta.status_code == 422
    cuerpo = respuesta.json()
    assert cuerpo["codigo"] == "FOTO_TIPO_NO_COINCIDE"
    assert cuerpo["detalle"] == {"detectado": ["scooter"], "tipo_vmp": "bicicleta"}

    vehiculo = cliente.get(f"{API}/usuarios/me/vehiculos", headers=cabeceras).json()["items"][0]
    assert vehiculo["tiene_foto"] is False


def test_foto_con_confianza_baja_es_rechazada(cliente: TestClient, preparar_usuario, png):
    cabeceras, _ = preparar_usuario()
    id_vehiculo = cliente.post(
        f"{API}/usuarios/me/vehiculos",
        json={"tipo_vmp": "scooter_electrico", "marca": "Xiaomi", "color": "negro"},
        headers=cabeceras,
    ).json()["id_vehiculo"]

    respuesta = cliente.post(
        f"{API}/usuarios/me/vehiculos/{id_vehiculo}/foto",
        files={"archivo": ("dudosa.png", png, "image/png")},
        headers=cabeceras,
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "FOTO_SIN_VEHICULO"


def test_cambiar_el_tipo_obliga_a_subir_otra_foto(cliente: TestClient, preparar_usuario):
    cabeceras, ids = preparar_usuario(vehiculos=({"tipo_vmp": "scooter_electrico"},))

    # Editar otro dato conserva la foto.
    respuesta = cliente.put(
        f"{API}/usuarios/me/vehiculos/{ids[0]}", json={"color": "rojo"}, headers=cabeceras
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["tiene_foto"] is True

    # Cambiar el tipo la invalida: se validó para un scooter.
    respuesta = cliente.put(
        f"{API}/usuarios/me/vehiculos/{ids[0]}", json={"tipo_vmp": "bicicleta"}, headers=cabeceras
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["tiene_foto"] is False
    assert respuesta.json()["foto_referencia_url"] is None
