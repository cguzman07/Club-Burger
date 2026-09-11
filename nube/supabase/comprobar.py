"""Comprueba o avisa si falta libro_ventas en Supabase. No imprime claves."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SQL = Path(__file__).resolve().parent / "schema.sql"


def leer_env() -> dict[str, str]:
    datos: dict[str, str] = {}
    for path in (ROOT / "local.env", ROOT / "panel_dueno" / "local.env"):
        if not path.exists():
            continue
        for linea in path.read_text(encoding="utf-8").splitlines():
            texto = linea.strip()
            if not texto or texto.startswith("#") or "=" not in texto:
                continue
            k, v = texto.split("=", 1)
            datos[k.strip()] = v.strip().strip('"').strip("'")
    return datos


def rest(url: str, key: str, method: str, path: str, body=None):
    datos = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        f"{url.rstrip('/')}{path}",
        data=datos,
        headers={
            "Authorization": f"Bearer {key}",
            "apikey": key,
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
        method=method,
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        raw = resp.read()
        return resp.status, raw.decode("utf-8") if raw else ""


def main() -> int:
    env = leer_env()
    url = os.environ.get("SUPABASE_URL") or env.get("SUPABASE_URL") or ""
    key = os.environ.get("SUPABASE_SERVICE_KEY") or env.get("SUPABASE_SERVICE_KEY") or ""
    if not url or not key:
        print("Faltan SUPABASE_URL o SUPABASE_SERVICE_KEY en local.env")
        return 1
    try:
        rest(url, key, "GET", "/rest/v1/libro_ventas?select=id&limit=1")
        print("OK libro_ventas ya existe")
        try:
            rest(
                url,
                key,
                "POST",
                "/rest/v1/rpc/reporte_ventas",
                {"p_desde": "2025-01-01", "p_hasta": "2025-12-31"},
            )
            print("OK funcion reporte_ventas")
        except urllib.error.HTTPError as e:
            print("Falta funcion reporte_ventas:", e.code)
            print("Ejecuta nube/supabase/schema.sql en el SQL Editor de Supabase")
            return 2
        return 0
    except urllib.error.HTTPError as e:
        detalle = e.read().decode("utf-8", "replace")[:300]
        print("libro_ventas no está lista:", e.code, detalle)
        print("Ejecuta nube/supabase/schema.sql en el SQL Editor de Supabase")
        print("Archivo:", SQL)
        return 2


if __name__ == "__main__":
    sys.exit(main())
