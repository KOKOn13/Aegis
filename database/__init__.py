"""Capa de persistencia basada en JSON para el sistema de centros de acopio."""

from .exceptions import DuplicateRecordError, InsufficientStockError, NotFoundError, PermissionDeniedError, ValidationError
from .json_manager import get_data_dir, load_json, save_json, set_data_dir

__all__ = [
    "ValidationError",
    "NotFoundError",
    "InsufficientStockError",
    "DuplicateRecordError",
    "PermissionDeniedError",
    "load_json",
    "save_json",
    "set_data_dir",
    "get_data_dir",
]
