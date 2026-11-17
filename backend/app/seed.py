"""Datos de ejemplo para la demo (docs/18 §8).

Uso:
    python -m app.seed            # crea lo que falte (idempotente)
    python -m app.seed --reset    # borra las tablas de negocio y vuelve a sembrar

Crea personal de seguridad (2 guardias + 1 administrador), sincroniza los
usuarios del Conector simulado, registra vehículos con foto de referencia y
emite un QR por usuario. Las fotos son sintéticas (PIL): sirven para que la
demo tenga imágenes, no como dataset del detector.
"""

from __future__ import annotations

import io
import os
import sys

from PIL import Image, ImageDraw
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.enums import RolPersonal, TurnoPersonal
from app.core.security import hash_password
from app.core.storage import guardar_imagen
from app.core.time import ahora
from app.modules.administracion.models import PersonalSeguridad
from app.modules.estacionamiento import service as estacionamiento
from app.modules.identidad import service as identidad
from app.modules.identidad.conector_utp.base import obtener_conector
from app.modules.identidad.models import VehiculoVMP

# El orden respeta las claves foráneas.
TABLAS_NEGOCIO = (
    "notificacion",
    "reporte_piloto",
    "incidencia",
    "evento_deteccion_ia",
    "intento_lectura_qr",
    "sesion_estacionamiento",
    "espacio_estacionamiento",
    "zona_estacionamiento",
    "codigo_qr",
    "vehiculo_vmp",
    "sincronizacion_utp",
    "usuario_utp",
    "personal_seguridad",
)

PERSONAL = (
    {
        "nombres": "Carlos",
        "apellidos": "Quispe Mamani",
        "usuario_acceso": "guardia.tarde",
        "password": "seguridad123",
        "turno": TurnoPersonal.tarde,
        "rol": RolPersonal.seguridad,
    },
    {
        "nombres": "Rosa",
        "apellidos": "Flores Nuñez",
        "usuario_acceso": "guardia.noche",
        "password": "seguridad123",
        "turno": TurnoPersonal.noche,
        "rol": RolPersonal.seguridad,
    },
    {
        "nombres": "Jefe",
        "apellidos": "de Seguridad",
        "usuario_acceso": "admin.seguridad",
        "password": "admin123",
        "turno": TurnoPersonal.manana,
        "rol": RolPersonal.administrador,
    },
)

# Vehículos por código UTP. `etiqueta` decide el dibujo de la foto sintética.
VEHICULOS = {
    "U90000001": [
        {
            "tipo_vmp": "scooter_electrico",
            "marca": "Xiaomi",
            "modelo": "Mi 3",
            "color": "negro",
            "caracteristica_distintiva": "sticker rojo en el manubrio",
            "etiqueta": "scooter",
        },
    ],
    "U90000002": [
        {
            "tipo_vmp": "bicicleta",
            "marca": "Trek",
            "modelo": "FX 2",
            "color": "azul",
            "caracteristica_distintiva": "parrilla trasera",
            "etiqueta": "bicicleta",
        },
    ],
    "U90000004": [
        {
            "tipo_vmp": "scooter_electrico",
            "marca": "Segway",
            "modelo": "Ninebot Max",
            "color": "gris",
            "caracteristica_distintiva": None,
            "etiqueta": "scooter",
        },
        {
            "tipo_vmp": "moto_electrica",
            "marca": "NIU",
            "modelo": "NQi",
            "color": "blanco",
            "caracteristica_distintiva": "baúl negro",
            "etiqueta": "moto",
        },
    ],
    "U90000003": [
        {
            "tipo_vmp": "bicicleta_electrica",
            "marca": "Specialized",
            "modelo": "Turbo Vado",
            "color": "verde",
            "caracteristica_distintiva": "luces LED",
            "etiqueta": "bicicleta",
        },
        {
            "tipo_vmp": "scooter_electrico",
            "marca": "Xiaomi",
            "modelo": "Pro 2",
            "color": "gris",
            "caracteristica_distintiva": None,
            "etiqueta": "scooter",
        },
        {
            "tipo_vmp": "bicicleta",
            "marca": "Aro",
            "modelo": "Montaña",
            "color": "rojo",
            "caracteristica_distintiva": "guardafango",
            "etiqueta": "bicicleta",
        },
    ],
}


# ---------------------------------------------------------------------
# Fotos sintéticas (no son dataset: solo para que la demo tenga imágenes)
# ---------------------------------------------------------------------
def _foto_sintetica(etiqueta: str, color_fondo: tuple[int, int, int]) -> bytes:
    imagen = Image.new("RGB", (640, 480), color_fondo)
    dibujo = ImageDraw.Draw(imagen)
    # Círculos que sugieren ruedas
    dibujo.ellipse((120, 250, 250, 380), outline=(30, 30, 30), width=12)
    dibujo.ellipse((390, 250, 520, 380), outline=(30, 30, 30), width=12)
    dibujo.line((185, 315, 455, 315), fill=(30, 30, 30), width=10)
    dibujo.line((185, 315, 330, 190), fill=(30, 30, 30), width=8)
    dibujo.line((455, 315, 380, 190), fill=(30, 30, 30), width=8)
    dibujo.text((20, 20), f"foto de referencia: {etiqueta}", fill=(255, 255, 255))
    buffer = io.BytesIO()
    imagen.save(buffer, format="JPEG", quality=88)
    return buffer.getvalue()


COLORES = {
    "scooter": (44, 62, 90),
    "bicicleta": (40, 70, 50),
    "moto": (80, 45, 70),
}


# ---------------------------------------------------------------------
# Siembra
# ---------------------------------------------------------------------
def _limpiar(db: Session) -> None:
    db.execute(text(f"TRUNCATE {', '.join(TABLAS_NEGOCIO)} RESTART IDENTITY CASCADE"))
    db.commit()


def _sembrar_personal(db: Session) -> list[PersonalSeguridad]:
    creados: list[PersonalSeguridad] = []
    for datos in PERSONAL:
        existente = db.scalar(
            select(PersonalSeguridad).where(
                PersonalSeguridad.usuario_acceso == datos["usuario_acceso"]
            )
        )
        if existente is not None:
            creados.append(existente)
            continue
        personal = PersonalSeguridad(
            nombres=datos["nombres"],
            apellidos=datos["apellidos"],
            usuario_acceso=datos["usuario_acceso"],
            contrasena_hash=hash_password(datos["password"]),
            turno=datos["turno"],
            rol=datos["rol"],
        )
        db.add(personal)
        db.flush()
        creados.append(personal)
    db.commit()
    return creados


def _con_vehiculos_de_ejemplo() -> bool:
    """`SEED_VEHICULOS=1` añade vehículos de ejemplo con fotos dibujadas.

    Apagado por defecto: para la demo, cada perfil empieza sin vehículos y los
    registra con su foto real en el Portal (docs/27).
    """
    return os.environ.get("SEED_VEHICULOS", "0").strip().lower() in {"1", "si", "sí", "true"}


def _sembrar_usuario(db: Session, codigo_utp: str) -> None:
    usuario = identidad.sincronizar_usuario(db, codigo_utp)
    # Con vehículos de ejemplo, el consentimiento se deja aceptado (lo exigen). Sin
    # ellos queda pendiente: en la demo el usuario lo acepta en el Portal (docs/27).
    if _con_vehiculos_de_ejemplo() and not usuario.acepta_tratamiento_datos:
        usuario.acepta_tratamiento_datos = True
        usuario.fecha_consentimiento = ahora()
        usuario.version_consentimiento = identidad.VERSION_CONSENTIMIENTO_ACTUAL
        db.commit()

    # Solo en un usuario que nunca tuvo vehículos: así no se pasa del máximo de 3
    # ni reaparecen vehículos que el usuario ya registró o dio de baja.
    ya_tiene = db.scalar(
        select(VehiculoVMP.id_vehiculo).where(VehiculoVMP.id_usuario_utp == usuario.id_usuario_utp)
    )
    ejemplos = (
        VEHICULOS.get(codigo_utp, []) if _con_vehiculos_de_ejemplo() and ya_tiene is None else []
    )
    for datos in ejemplos:
        existente = db.scalar(
            select(VehiculoVMP).where(
                VehiculoVMP.id_usuario_utp == usuario.id_usuario_utp,
                VehiculoVMP.marca == datos["marca"],
                VehiculoVMP.modelo == datos["modelo"],
            )
        )
        if existente is not None:
            continue
        imagen = _foto_sintetica(datos["etiqueta"], COLORES[datos["etiqueta"]])
        key = guardar_imagen(imagen, f"referencias/{usuario.id_usuario_utp}")
        db.add(
            VehiculoVMP(
                id_usuario_utp=usuario.id_usuario_utp,
                tipo_vmp=datos["tipo_vmp"],
                marca=datos["marca"],
                modelo=datos["modelo"],
                color=datos["color"],
                caracteristica_distintiva=datos["caracteristica_distintiva"],
                foto_referencia_url=key,
            )
        )
        db.commit()

    identidad.obtener_qr(db, usuario)


def ejecutar(reset: bool = False) -> None:
    conector = obtener_conector()
    if not hasattr(conector, "todos"):
        raise SystemExit("El seed solo funciona con el Conector UTP simulado.")

    db = SessionLocal()
    try:
        if reset:
            print("Limpiando tablas de negocio…")
            _limpiar(db)

        personal = _sembrar_personal(db)
        print(f"Personal de seguridad: {len(personal)}")

        estacionamiento.asegurar_espacios(db)
        print("Espacios: 5 zonas (A-E) x 8 = 40")

        for datos in conector.todos():  # type: ignore[attr-defined]
            _sembrar_usuario(db, datos.codigo_utp)
            print(f"Usuario sembrado: {datos.codigo_utp} ({datos.nombres} {datos.apellidos})")

        print("\n--- Identidades de ejemplo ---")
        for p in personal:
            print(f"  guardia  {p.usuario_acceso:<18} contraseña de referencia en app/seed.py")
        for datos in conector.todos():  # type: ignore[attr-defined]
            print(f"  usuario  {datos.codigo_utp:<12} {datos.nombres} {datos.apellidos}")
        print(
            "\nToken de desarrollo:\n"
            "  POST /api/v1/dev/sesion/usuario/U90000001\n"
            "  POST /api/v1/dev/sesion/guardia/guardia.tarde\n"
        )
    finally:
        db.close()


def main() -> None:
    ejecutar(reset="--reset" in sys.argv[1:])


if __name__ == "__main__":
    main()
