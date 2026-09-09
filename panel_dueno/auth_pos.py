"""Login con los mismos usuarios del POS (tabla usuarios). No toca Club Burger.exe."""

from __future__ import annotations

import sqlite3
from typing import Any

from snapshot import _connect, _rows

ROLES_ADMIN = {"admin", "administrador", "dueño", "dueno", "owner", "jefe"}

# GoTrue exige contraseña de 6+ caracteres; el POS puede tener claves más cortas.
AUTH_DOMINIO = "usuarios.clubburger"
AUTH_CLAVE_EXTRA = "#cb"


def es_admin(rol: str | None) -> bool:
    return (rol or "").strip().lower() in ROLES_ADMIN


def email_pos(usuario: str) -> str:
    slug = "".join(ch for ch in usuario.strip().lower() if ch.isalnum() or ch in "._-") or "usuario"
    return f"{slug}@{AUTH_DOMINIO}"


def clave_auth(contrasena: str) -> str:
    return f"{contrasena}{AUTH_CLAVE_EXTRA}"


def autenticar(usuario: str, contrasena: str) -> dict[str, Any] | None:
    nombre = (usuario or "").strip()
    clave = contrasena or ""
    if not nombre or not clave:
        return None
    conn = _connect()
    try:
        filas = _rows(conn, "SELECT id, usuario, contrasena, rol FROM usuarios")
    except sqlite3.Error:
        return None
    finally:
        conn.close()

    for fila in filas:
        guardado = str(fila["usuario"] or "")
        if guardado != nombre and guardado.lower() != nombre.lower():
            continue
        actual = str(fila["contrasena"] or "")
        if actual != clave:
            return None
        rol = str(fila["rol"] or "cajero").strip() or "cajero"
        return {
            "id": int(fila["id"]),
            "usuario": guardado,
            "rol": rol,
            "es_admin": es_admin(rol),
        }
    return None


def filtrar_estado(estado: dict[str, Any], sesion: dict[str, Any] | None) -> dict[str, Any]:
    data = dict(estado or {})
    rol = (sesion or {}).get("rol") or "cajero"
    admin = es_admin(rol)
    data["sesion"] = {
        "usuario": (sesion or {}).get("usuario") or "—",
        "rol": rol,
        "es_admin": admin,
    }
    if not admin:
        data.pop("reporte", None)
    return data
