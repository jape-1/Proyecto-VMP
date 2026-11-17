"""Importa todos los modelos para que `Base.metadata` esté completo.

Lo usan Alembic y las pruebas. No importar modelos sueltos por ahí: cada módulo
es dueño de sus tablas (docs/04 §7).
"""

from app.modules.administracion import models as _administracion  # noqa: F401
from app.modules.estacionamiento import models as _estacionamiento  # noqa: F401
from app.modules.identidad import models as _identidad  # noqa: F401
from app.modules.notificaciones import models as _notificaciones  # noqa: F401

__all__ = ["_administracion", "_estacionamiento", "_identidad", "_notificaciones"]
