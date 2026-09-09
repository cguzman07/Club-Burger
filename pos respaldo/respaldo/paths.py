"""
Rutas de la app: modo desarrollo y ejecutable (.exe / PyInstaller).
- Recursos empaquetados (logo, icono) → _MEIPASS
- Datos escribibles (BD, factura, config impresora) → carpeta del .exe
"""
from __future__ import annotations

import os
import sys


def frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_dir() -> str:
    """Carpeta del ejecutable o del proyecto (respaldo/)."""
    if frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def resource_dir() -> str:
    """Carpeta de recursos embebidos (assets en el bundle)."""
    if frozen():
        return getattr(sys, "_MEIPASS", app_dir())
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(*parts: str) -> str:
    return os.path.join(resource_dir(), *parts)


def data_path(*parts: str) -> str:
    """Archivos que se escriben junto al .exe (o en desarrollo)."""
    return os.path.join(app_dir(), *parts)


def asset_path(*parts: str) -> str:
    """assets/... tanto en desarrollo como empaquetado."""
    candidates = [
        resource_path("assets", *parts),
        os.path.join(app_dir(), "assets", *parts),
        resource_path(*parts),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]


def icon_ico_path() -> str:
    return asset_path("club_burger.ico")


def logo_ui_path() -> str:
    return asset_path("club_burger_logo.png")
