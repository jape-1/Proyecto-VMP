"""Espacios: asignación al validar el ingreso y monitoreo básico (17-nov-2026, docs/13).

Sin cámaras de casillas todavía (HU13–HU15): el sistema asigna el primer espacio
libre al validar el ingreso y el guardia lo libera a mano en el monitoreo.
"""

from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.enums import EstadoEspacio
from app.modules.estacionamiento import service
from app.modules.estacionamiento.models import EspacioEstacionamiento, SesionEstacionamiento
from tests.conftest import API
from tests.test_acceso import _capturar, _leer_qr


def _espacios(db: Session, zonas: str = "AB", por_zona: int = 2) -> None:
    service.asegurar_espacios(db, zonas=zonas, por_zona=por_zona)


def _ingresar(cliente, guardia, token_qr, codigo="U90000001") -> dict:
    id_sesion = _leer_qr(cliente, guardia, token_qr(codigo))["id_sesion"]
    _capturar(cliente, guardia, id_sesion)
    return cliente.get(f"{API}/acceso/{id_sesion}", headers=guardia).json()


def test_al_validar_se_asigna_el_primer_espacio_libre(
    cliente: TestClient, preparar_usuario, token_guardia, token_qr, db: Session
):
    _espacios(db)
    preparar_usuario(vehiculos=({"tipo_vmp": "scooter_electrico"},))
    preparar_usuario("U90000002", vehiculos=({"tipo_vmp": "scooter_electrico"},))
    guardia = token_guardia()

    primero = _ingresar(cliente, guardia, token_qr)
    assert primero["estado"] == "validado"
    assert primero["espacio"] == "A-01"

    segundo = _ingresar(cliente, guardia, token_qr, "U90000002")
    assert segundo["espacio"] == "A-02"

    ocupados = db.scalars(
        select(EspacioEstacionamiento.codigo_espacio).where(
            EspacioEstacionamiento.estado == EstadoEspacio.ocupado
        )
    ).all()
    assert sorted(ocupados) == ["A-01", "A-02"]


def test_sin_validar_no_se_asigna_espacio(
    cliente: TestClient, preparar_usuario, token_guardia, token_qr, db: Session
):
    _espacios(db)
    preparar_usuario(vehiculos=({"tipo_vmp": "scooter_electrico"},))
    guardia = token_guardia()
    id_sesion = _leer_qr(cliente, guardia, token_qr())["id_sesion"]
    _capturar(cliente, guardia, id_sesion, "scooter-distinto.png")

    estado = cliente.get(f"{API}/acceso/{id_sesion}", headers=guardia).json()
    assert estado["estado"] == "verificar"
    assert estado["espacio"] is None

    # El guardia aprueba a mano: ahí sí se asigna.
    aprobado = cliente.post(
        f"{API}/acceso/{id_sesion}/decision",
        json={"decision": "aprobar_manual", "motivo": "Es su scooter, lo verifiqué"},
        headers=guardia,
    ).json()
    assert aprobado["estado"] == "validado"
    assert aprobado["espacio"] == "A-01"


def test_estacionamiento_lleno_no_deja_leer_el_qr(
    cliente: TestClient, preparar_usuario, token_guardia, token_qr, db: Session
):
    _espacios(db, zonas="A", por_zona=1)
    preparar_usuario(vehiculos=({"tipo_vmp": "scooter_electrico"},))
    preparar_usuario("U90000002", vehiculos=({"tipo_vmp": "scooter_electrico"},))
    guardia = token_guardia()
    assert _ingresar(cliente, guardia, token_qr)["espacio"] == "A-01"

    respuesta = cliente.post(
        f"{API}/acceso/qr", json={"token": token_qr("U90000002")}, headers=guardia
    )
    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "ESTACIONAMIENTO_LLENO"


def test_un_espacio_en_mantenimiento_no_se_asigna(
    cliente: TestClient, preparar_usuario, token_guardia, token_qr, db: Session
):
    _espacios(db, zonas="A", por_zona=2)
    db.execute(
        update(EspacioEstacionamiento)
        .where(EspacioEstacionamiento.codigo_espacio == "A-01")
        .values(estado=EstadoEspacio.mantenimiento)
    )
    db.commit()
    preparar_usuario(vehiculos=({"tipo_vmp": "scooter_electrico"},))
    assert _ingresar(cliente, token_guardia(), token_qr)["espacio"] == "A-02"


def test_monitoreo_cuenta_espacios_y_muestra_quien_ocupa(
    cliente: TestClient, preparar_usuario, token_guardia, token_qr, db: Session
):
    _espacios(db)
    preparar_usuario(vehiculos=({"tipo_vmp": "scooter_electrico", "marca": "Xiaomi"},))
    guardia = token_guardia()
    _ingresar(cliente, guardia, token_qr)

    resumen = cliente.get(f"{API}/espacios", headers=guardia).json()
    assert resumen["total"] == 4
    assert resumen["libres"] == 3
    assert resumen["ocupados"] == 1
    assert resumen["lleno"] is False
    assert [z["nombre"] for z in resumen["zonas"]] == ["A", "B"]

    a01 = resumen["zonas"][0]["espacios"][0]
    assert a01["codigo"] == "A-01"
    assert a01["estado"] == "ocupado"
    assert a01["ocupante"]["codigo_utp"] == "U90000001"
    assert a01["ocupante"]["vehiculo"]["marca"] == "Xiaomi"
    assert a01["ocupante"]["desde"]
    assert resumen["zonas"][0]["espacios"][1]["ocupante"] is None


def test_el_usuario_no_ve_el_monitoreo(cliente: TestClient, preparar_usuario, db: Session):
    """RF21: la vista detallada de espacios es solo de seguridad y administración."""
    _espacios(db)
    cabeceras, _ = preparar_usuario()
    assert cliente.get(f"{API}/espacios", headers=cabeceras).status_code == 403


def test_liberar_un_espacio_cierra_el_ingreso_y_permite_volver(
    cliente: TestClient, preparar_usuario, token_guardia, token_qr, db: Session
):
    _espacios(db)
    preparar_usuario(vehiculos=({"tipo_vmp": "scooter_electrico"},))
    guardia = token_guardia()
    primero = _ingresar(cliente, guardia, token_qr)
    id_espacio = db.scalar(
        select(EspacioEstacionamiento.id_espacio).where(
            EspacioEstacionamiento.codigo_espacio == "A-01"
        )
    )

    resumen = cliente.post(f"{API}/espacios/{id_espacio}/liberar", headers=guardia).json()
    assert resumen["libres"] == 4

    sesion = db.get(SesionEstacionamiento, primero["id_sesion"])
    db.refresh(sesion)
    assert sesion.fecha_hora_salida is not None
    assert sesion.estado_sesion.value == "finalizada"

    # El mismo vehículo vuelve a entrar y se valida solo.
    assert _ingresar(cliente, guardia, token_qr)["estado"] == "validado"


def test_salida_de_demo_tambien_libera_el_espacio(
    cliente: TestClient, preparar_usuario, token_guardia, token_qr, db: Session
):
    _espacios(db)
    preparar_usuario(vehiculos=({"tipo_vmp": "scooter_electrico"},))
    guardia = token_guardia()
    _ingresar(cliente, guardia, token_qr)
    cliente.post(f"{API}/dev/salida/U90000001")
    assert cliente.get(f"{API}/espacios", headers=guardia).json()["libres"] == 4


def test_sin_espacios_configurados_el_ingreso_funciona_igual(
    cliente: TestClient, preparar_usuario, token_guardia, token_qr
):
    """Antes de configurar las zonas, nada se bloquea: solo no hay espacio que asignar."""
    preparar_usuario(vehiculos=({"tipo_vmp": "scooter_electrico"},))
    estado = _ingresar(cliente, token_guardia(), token_qr)
    assert estado["estado"] == "validado"
    assert estado["espacio"] is None


def test_asegurar_espacios_no_duplica(db: Session):
    service.asegurar_espacios(db)
    service.asegurar_espacios(db)
    assert len(db.scalars(select(EspacioEstacionamiento)).all()) == 40
