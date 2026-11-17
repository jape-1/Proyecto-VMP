"""Endpoints del frontend del usuario (docs/18 §6)."""

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.gateway.deps import usuario_actual
from app.modules.identidad import service
from app.modules.identidad.models import UsuarioUTP
from app.modules.identidad.schemas import (
    ListaVehiculosOut,
    PerfilOut,
    PerfilUpdate,
    QROut,
    VehiculoCreadoOut,
    VehiculoIn,
    VehiculoOut,
    VehiculoUpdate,
)

router = APIRouter(prefix="/usuarios/me", tags=["Usuario"])


@router.get("", response_model=PerfilOut, summary="Perfil del usuario (HU01)")
def mi_perfil(
    db: Session = Depends(get_db), usuario: UsuarioUTP = Depends(usuario_actual)
) -> PerfilOut:
    """Devuelve el perfil tal como lo entrega el Conector UTP simulado."""
    actualizado = service.sincronizar_usuario(db, usuario.codigo_utp)
    return service.perfil_out(actualizado)


@router.put(
    "/perfil",
    response_model=PerfilOut,
    summary="Completa el perfil y registra el consentimiento (HU01)",
)
def actualizar_mi_perfil(
    datos: PerfilUpdate,
    db: Session = Depends(get_db),
    usuario: UsuarioUTP = Depends(usuario_actual),
) -> PerfilOut:
    actualizado = service.actualizar_perfil(db, usuario, datos)
    return service.perfil_out(actualizado)


@router.get(
    "/vehiculos",
    response_model=ListaVehiculosOut,
    summary="Lista los VMP activos y el cupo usado (HU02/HU04)",
)
def mis_vehiculos(
    db: Session = Depends(get_db), usuario: UsuarioUTP = Depends(usuario_actual)
) -> ListaVehiculosOut:
    return service.listar_vehiculos(db, usuario)


@router.post(
    "/vehiculos",
    response_model=VehiculoCreadoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registra un VMP; máximo 3 activos (HU02)",
)
def crear_mi_vehiculo(
    datos: VehiculoIn,
    db: Session = Depends(get_db),
    usuario: UsuarioUTP = Depends(usuario_actual),
) -> VehiculoCreadoOut:
    vehiculo = service.crear_vehiculo(db, usuario, datos)
    return VehiculoCreadoOut(id_vehiculo=vehiculo.id_vehiculo, estado=vehiculo.estado)


@router.put(
    "/vehiculos/{id_vehiculo}",
    response_model=VehiculoOut,
    summary="Edita un VMP propio (HU04)",
)
def editar_mi_vehiculo(
    id_vehiculo: int,
    datos: VehiculoUpdate,
    db: Session = Depends(get_db),
    usuario: UsuarioUTP = Depends(usuario_actual),
) -> VehiculoOut:
    return service.vehiculo_out(service.editar_vehiculo(db, usuario, id_vehiculo, datos))


@router.delete(
    "/vehiculos/{id_vehiculo}",
    response_model=VehiculoOut,
    summary="Da de baja lógica un VMP propio (HU04)",
)
def eliminar_mi_vehiculo(
    id_vehiculo: int,
    db: Session = Depends(get_db),
    usuario: UsuarioUTP = Depends(usuario_actual),
) -> VehiculoOut:
    return service.vehiculo_out(service.dar_baja_vehiculo(db, usuario, id_vehiculo))


@router.post(
    "/vehiculos/{id_vehiculo}/foto",
    response_model=VehiculoOut,
    summary="Sube la foto de referencia validada por el detector (HU03)",
)
def subir_foto_referencia(
    id_vehiculo: int,
    archivo: UploadFile = File(..., description="JPG o PNG, máximo 5 MB"),
    db: Session = Depends(get_db),
    usuario: UsuarioUTP = Depends(usuario_actual),
) -> VehiculoOut:
    contenido = archivo.file.read()
    vehiculo = service.guardar_foto_referencia(
        db,
        usuario,
        id_vehiculo,
        contenido,
        archivo.content_type,
        archivo.filename or "referencia.jpg",
    )
    return service.vehiculo_out(vehiculo)


@router.get("/qr", response_model=QROut, summary="QR vigente del usuario (HU05/HU06)")
def mi_qr(db: Session = Depends(get_db), usuario: UsuarioUTP = Depends(usuario_actual)) -> QROut:
    qr = service.obtener_qr(db, usuario)
    return service.qr_out(db, usuario, qr)


@router.post(
    "/qr/regenerar",
    response_model=QROut,
    summary="Revoca el QR actual y emite uno nuevo (HU05)",
)
def regenerar_mi_qr(
    db: Session = Depends(get_db), usuario: UsuarioUTP = Depends(usuario_actual)
) -> QROut:
    qr = service.regenerar_qr(db, usuario)
    return service.qr_out(db, usuario, qr)
