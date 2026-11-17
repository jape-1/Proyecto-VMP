"""Sesión «ya iniciada» para desarrollo (docs/18 §4).

Estos endpoints **no existen fuera de `ENTORNO=dev`**: devuelven un token sin
contraseña, así que en producción serían una puerta trasera. El router se
registra solo en desarrollo (`app/main.py`) y además cada handler vuelve a
comprobarlo.
"""

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.enums import EstadoActivo
from app.core.errors import ErrorNegocio
from app.core.security import crear_token
from app.modules.administracion.models import PersonalSeguridad
from app.modules.estacionamiento import service as estacionamiento
from app.modules.identidad import service as identidad
from app.modules.identidad.conector_utp.base import ConectorSimulado, obtener_conector

router = APIRouter(prefix="/dev", tags=["Desarrollo"])


def _solo_dev() -> None:
    if not settings.es_dev:
        # 404 a propósito: ni siquiera se revela que la ruta existe.
        raise ErrorNegocio("NO_ENCONTRADO", "Recurso no encontrado.", 404)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expira_en_seg: int
    rol: str
    id: int
    nombre: str
    detalle: dict


@router.post(
    "/sesion/usuario/{codigo_utp}",
    response_model=TokenOut,
    status_code=status.HTTP_200_OK,
    summary="Token de un usuario UTP de ejemplo (solo dev)",
)
def sesion_usuario(
    codigo_utp: str,
    db: Session = Depends(get_db),
    _: None = Depends(_solo_dev),
) -> TokenOut:
    usuario = identidad.sincronizar_usuario(db, codigo_utp)
    token, expira = crear_token(sub=usuario.id_usuario_utp, rol="usuario")
    return TokenOut(
        access_token=token,
        expira_en_seg=expira,
        rol="usuario",
        id=usuario.id_usuario_utp,
        nombre=f"{usuario.nombres} {usuario.apellidos}",
        detalle={
            "codigo_utp": usuario.codigo_utp,
            "consentimiento": usuario.acepta_tratamiento_datos,
            "estado_matricula": usuario.estado_matricula.value,
        },
    )


@router.post(
    "/sesion/guardia/{usuario_acceso}",
    response_model=TokenOut,
    status_code=status.HTTP_200_OK,
    summary="Token de un guardia de ejemplo (solo dev)",
)
def sesion_guardia(
    usuario_acceso: str,
    db: Session = Depends(get_db),
    _: None = Depends(_solo_dev),
) -> TokenOut:
    personal = db.scalar(
        select(PersonalSeguridad).where(PersonalSeguridad.usuario_acceso == usuario_acceso)
    )
    if personal is None or personal.estado != EstadoActivo.activo:
        raise ErrorNegocio(
            "PERSONAL_INEXISTENTE",
            f"No existe un guardia activo con usuario '{usuario_acceso}'.",
            404,
            {"sugerencia": "corre `python -m app.seed` o mira GET /api/v1/dev/identidades"},
        )
    token, expira = crear_token(sub=personal.id_personal, rol=personal.rol.value)
    return TokenOut(
        access_token=token,
        expira_en_seg=expira,
        rol=personal.rol.value,
        id=personal.id_personal,
        nombre=f"{personal.nombres} {personal.apellidos}",
        detalle={"turno": personal.turno.value},
    )


@router.get(
    "/qr/{codigo_utp}",
    summary="Texto del QR de un usuario, para la demo (solo dev)",
)
def qr_texto(
    codigo_utp: str,
    db: Session = Depends(get_db),
    _: None = Depends(_solo_dev),
) -> dict:
    """Devuelve el token en claro del QR vigente.

    La API normal **nunca** devuelve el token (solo el PNG): esto existe para que
    la demo y el frontend del guardia puedan simular la lectura sin cámara.
    """
    usuario = identidad.sincronizar_usuario(db, codigo_utp)
    qr = identidad.obtener_qr(db, usuario)
    return {
        "id_qr": qr.id_qr,
        "token": identidad.token_de_qr(qr),
        "estado": qr.estado.value,
        "fecha_expiracion": qr.fecha_expiracion.isoformat(),
        "vehiculos": [v.id_vehiculo for v in identidad.vehiculos_activos(db, usuario)],
    }


@router.post(
    "/salida/{codigo_utp}",
    summary="Registra la salida de los vehículos de un usuario, para repetir la demo (solo dev)",
)
def salida_de_demo(
    codigo_utp: str,
    db: Session = Depends(get_db),
    _: None = Depends(_solo_dev),
) -> dict:
    """Este avance no registra salidas (docs/18 §2): sin esto, un vehículo validado
    quedaría «dentro» para siempre y no se podría repetir el ingreso."""
    usuario = identidad.sincronizar_usuario(db, codigo_utp)
    cerradas = estacionamiento.registrar_salida_de_demo(db, usuario.id_usuario_utp)
    return {"codigo_utp": usuario.codigo_utp, "salidas_registradas": cerradas}


@router.get(
    "/identidades",
    summary="Identidades de ejemplo disponibles (solo dev)",
)
def identidades(
    db: Session = Depends(get_db),
    _: None = Depends(_solo_dev),
) -> dict:
    """Lista para que los frontends sepan qué identidad fija configurar al arrancar."""
    conector = obtener_conector()
    # `todos()` es propio del conector simulado: el real no puede enumerar usuarios.
    ejemplos = conector.todos() if isinstance(conector, ConectorSimulado) else []
    usuarios = [
        {
            "codigo_utp": u.codigo_utp,
            "nombres": u.nombres,
            "apellidos": u.apellidos,
            "tipo_usuario": u.tipo_usuario.value,
            "estado_matricula": u.estado_matricula.value,
            "ruta_sesion": f"/api/v1/dev/sesion/usuario/{u.codigo_utp}",
        }
        for u in ejemplos
    ]
    guardias = [
        {
            "usuario_acceso": p.usuario_acceso,
            "nombres": p.nombres,
            "apellidos": p.apellidos,
            "rol": p.rol.value,
            "turno": p.turno.value,
            "ruta_sesion": f"/api/v1/dev/sesion/guardia/{p.usuario_acceso}",
        }
        for p in db.scalars(
            select(PersonalSeguridad)
            .where(PersonalSeguridad.estado == EstadoActivo.activo)
            .order_by(PersonalSeguridad.id_personal)
        )
    ]
    return {"usuarios": usuarios, "guardia": guardias}
