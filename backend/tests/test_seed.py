"""Datos de ejemplo: por defecto los perfiles empiezan sin vehículos (docs/27)."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import seed
from app.modules.estacionamiento.models import EspacioEstacionamiento
from app.modules.identidad.models import UsuarioUTP, VehiculoVMP


def _vehiculos(db: Session) -> int:
    db.expire_all()
    return db.scalar(select(func.count()).select_from(VehiculoVMP)) or 0


def test_por_defecto_crea_espacios_y_ningun_vehiculo(db: Session, monkeypatch):
    monkeypatch.delenv("SEED_VEHICULOS", raising=False)
    seed.ejecutar()
    assert _vehiculos(db) == 0
    assert db.scalar(select(func.count()).select_from(EspacioEstacionamiento)) == 40
    # El consentimiento queda pendiente: se acepta en el Portal, frente a la cámara.
    assert not db.scalar(
        select(func.count()).select_from(UsuarioUTP).where(UsuarioUTP.acepta_tratamiento_datos)
    )


def test_con_ejemplos_no_duplica_al_arrancar_otra_vez(db: Session, monkeypatch):
    monkeypatch.setenv("SEED_VEHICULOS", "1")
    seed.ejecutar()
    cantidad = _vehiculos(db)
    assert cantidad == sum(len(v) for v in seed.VEHICULOS.values())
    seed.ejecutar()
    assert _vehiculos(db) == cantidad


def test_con_ejemplos_respeta_al_usuario_que_ya_registro(
    db: Session, monkeypatch, preparar_usuario
):
    """Quien ya registró un vehículo no recibe ejemplos (no se pasa del máximo de 3)."""
    preparar_usuario("U90000003", vehiculos=({"tipo_vmp": "scooter_electrico"},))
    monkeypatch.setenv("SEED_VEHICULOS", "1")
    seed.ejecutar()
    db.expire_all()
    suyos = db.scalar(
        select(func.count())
        .select_from(VehiculoVMP)
        .join(UsuarioUTP, UsuarioUTP.id_usuario_utp == VehiculoVMP.id_usuario_utp)
        .where(UsuarioUTP.codigo_utp == "U90000003")
    )
    assert suyos == 1
