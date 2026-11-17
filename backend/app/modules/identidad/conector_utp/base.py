"""Conector/Adaptador UTP: única pieza que «sabe» de la UTP (docs/04 §2)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.core.enums import EstadoMatricula, TipoUsuario
from app.core.errors import ErrorNegocio

DATOS_SIMULADOS = Path(__file__).with_name("usuarios.json")


@dataclass(frozen=True)
class UsuarioUTPData:
    codigo_utp: str
    tipo_usuario: TipoUsuario
    nombres: str
    apellidos: str
    correo_institucional: str
    sede: str
    estado_matricula: EstadoMatricula


class ConectorUTP(Protocol):
    def obtener_usuario(self, codigo_utp: str) -> UsuarioUTPData: ...

    def esta_matriculado(self, codigo_utp: str) -> bool: ...


class ConectorSimulado:
    """Lee los datos de un JSON local: simula el Portal UTP, que no tenemos."""

    def __init__(self, ruta: Path | None = None) -> None:
        self.ruta = ruta or DATOS_SIMULADOS
        self._datos = self._cargar()

    def _cargar(self) -> dict[str, UsuarioUTPData]:
        crudos = json.loads(self.ruta.read_text(encoding="utf-8"))
        return {
            u["codigo_utp"]: UsuarioUTPData(
                codigo_utp=u["codigo_utp"],
                tipo_usuario=TipoUsuario(u["tipo_usuario"]),
                nombres=u["nombres"],
                apellidos=u["apellidos"],
                correo_institucional=u["correo_institucional"],
                sede=u["sede"],
                estado_matricula=EstadoMatricula(u["estado_matricula"]),
            )
            for u in crudos
        }

    def obtener_usuario(self, codigo_utp: str) -> UsuarioUTPData:
        datos = self._datos.get(codigo_utp.strip().upper())
        if datos is None:
            raise ErrorNegocio(
                "USUARIO_INEXISTENTE",
                "El código UTP no existe en el Portal UTP.",
                404,
                {"codigo_utp": codigo_utp},
            )
        return datos

    def esta_matriculado(self, codigo_utp: str) -> bool:
        try:
            return self.obtener_usuario(codigo_utp).estado_matricula == EstadoMatricula.activo
        except ErrorNegocio:
            return False

    def todos(self) -> list[UsuarioUTPData]:
        return list(self._datos.values())


@lru_cache
def obtener_conector() -> ConectorUTP:
    return ConectorSimulado()
