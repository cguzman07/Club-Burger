"""Sincroniza la caja local con Supabase y procesa pedidos del celular."""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from auth_pos import clave_auth, email_pos
from snapshot import db_path, _connect, _rows
from ticket import _printer_name
from ventas import VentaError, registrar_venta

ROOT = Path(__file__).resolve().parent
APP_ROOT = ROOT.parent
NUBE_ENV_FILES = (
    APP_ROOT / "local.env",
    ROOT / "local.env",
    ROOT / "nube.env",
)
STATE_PATH = ROOT / "nube_state.json"


def _leer_env_archivo() -> dict[str, str]:
    datos: dict[str, str] = {}
    for path in NUBE_ENV_FILES:
        if not path.exists():
            continue
        for linea in path.read_text(encoding="utf-8").splitlines():
            texto = linea.strip()
            if not texto or texto.startswith("#") or "=" not in texto:
                continue
            clave, valor = texto.split("=", 1)
            datos[clave.strip()] = valor.strip().strip('"').strip("'")
    return datos


def credenciales_nube() -> tuple[str, str]:
    archivo = _leer_env_archivo()
    url = os.environ.get("SUPABASE_URL") or archivo.get("SUPABASE_URL") or ""
    key = (
        os.environ.get("SUPABASE_SERVICE_KEY")
        or archivo.get("SUPABASE_SERVICE_KEY")
        or ""
    )
    return url.strip(), key.strip()


def url_publica() -> str:
    archivo = _leer_env_archivo()
    return (os.environ.get("PANEL_PUBLICO_URL") or archivo.get("PANEL_PUBLICO_URL") or "").strip()


def nube_activa() -> bool:
    url, key = credenciales_nube()
    if not url or not key:
        return False
    if "TU-PROYECTO" in url or key.endswith("..."):
        return False
    return url.startswith("http") and len(key) > 40


def _cliente():
    url, key = credenciales_nube()
    if not url or not key:
        return None
    from supabase import create_client

    return create_client(url, key)


def _json_safe(valor: Any) -> Any:
    if isinstance(valor, dict):
        return {str(k): _json_safe(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [_json_safe(v) for v in valor]
    return valor


def _cargar_estado_sync() -> dict[str, Any]:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"ultima_firma": "", "ultimo_error": None}


def _guardar_estado_sync(data: dict[str, Any]) -> None:
    STATE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _filas_sqlite() -> dict[str, list[dict[str, Any]]]:
    conn = _connect()
    try:
        productos = [
            {
                "id": r["id"],
                "nombre": r["nombre"],
                "categoria": r["categoria"],
                "precio": r["precio"],
                "stock": r["stock"],
                "stock_inicial": r["stock_inicial"],
            }
            for r in _rows(conn, "SELECT * FROM productos")
        ]
        caja = []
        for r in _rows(conn, "SELECT * FROM caja"):
            caja.append(
                {
                    "id": r["id"],
                    "usuario": r["usuario"],
                    "fecha": r["fecha"],
                    "hora_apertura": r["hora_apertura"],
                    "capital_inicial": r["capital_inicial"],
                    "detalle_capital": r["detalle_capital"],
                    "hora_cierre": r["hora_cierre"],
                    "capital_final": r["capital_final"],
                    "total_ventas": r["total_ventas"],
                    "fecha_cierre": r["fecha_cierre"],
                }
            )
        ventas = []
        for r in _rows(conn, "SELECT * FROM ventas"):
            ventas.append(
                {
                    "id": r["id"],
                    "fecha": r["fecha"],
                    "producto_id": r["producto_id"],
                    "nombre_producto": r["nombre_producto"],
                    "cantidad": r["cantidad"],
                    "precio_unitario": r["precio_unitario"],
                    "total": r["total"],
                    "metodo_pago": r["metodo_pago"],
                    "id_caja": r["id_caja"],
                    "nota": r["nota"],
                }
            )
        return {"productos": productos, "caja": caja, "ventas": ventas}
    finally:
        conn.close()


def _auth_admin(method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    url, key = credenciales_nube()
    datos = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        f"{url.rstrip('/')}/auth/v1{path}",
        data=datos,
        headers={
            "Authorization": f"Bearer {key}",
            "apikey": key,
            "Content-Type": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read()
            return json.loads(raw.decode("utf-8")) if raw else None
    except urllib.error.HTTPError as e:
        detalle = e.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"Auth {method} {path} → {e.code}: {detalle}") from e


def _firma_usuarios() -> str:
    conn = _connect()
    try:
        filas = _rows(conn, "SELECT usuario, rol, contrasena FROM usuarios ORDER BY id")
    except Exception:
        return ""
    finally:
        conn.close()
    partes = [f"{r['usuario']}|{r['rol']}|{r['contrasena']}" for r in filas]
    return hashlib.sha256("\n".join(partes).encode("utf-8")).hexdigest()


def sincronizar_usuarios_pos(sync: dict[str, Any]) -> None:
    """Crea/actualiza en Supabase Auth las mismas cuentas del POS (usuario + contraseña)."""
    firma = _firma_usuarios()
    if not firma:
        return
    if sync.get("firma_usuarios") == firma and not sync.get("ultimo_error_auth"):
        return
    conn = _connect()
    try:
        filas = _rows(conn, "SELECT usuario, rol, contrasena FROM usuarios")
    finally:
        conn.close()
    existentes: dict[str, str] = {}
    page = 1
    while page <= 10:
        lista = _auth_admin("GET", f"/admin/users?page={page}&per_page=200") or {}
        users = lista.get("users") if isinstance(lista, dict) else lista
        if not users:
            break
        for user in users:
            email = str((user or {}).get("email") or "").lower()
            uid = str((user or {}).get("id") or "")
            if email and uid:
                existentes[email] = uid
        if len(users) < 200:
            break
        page += 1
    hubo_error = False
    for fila in filas:
        usuario = str(fila["usuario"] or "").strip()
        if not usuario:
            continue
        email = email_pos(usuario)
        rol = str(fila["rol"] or "cajero").strip() or "cajero"
        payload = {
            "email": email,
            "password": clave_auth(str(fila["contrasena"] or "")),
            "email_confirm": True,
            "user_metadata": {"usuario": usuario, "rol": rol, "pos": True},
        }
        uid = existentes.get(email.lower())
        try:
            if uid:
                _auth_admin(
                    "PUT",
                    f"/admin/users/{uid}",
                    {
                        "password": payload["password"],
                        "email_confirm": True,
                        "user_metadata": payload["user_metadata"],
                    },
                )
            else:
                _auth_admin("POST", "/admin/users", payload)
        except Exception as exc:
            hubo_error = True
            sync["ultimo_error_auth"] = f"{usuario}: {exc}"[:400]
            continue
    if not hubo_error:
        sync["firma_usuarios"] = firma
        sync["ultimo_error_auth"] = None


def subir_estado(payload: dict[str, Any]) -> None:
    client = _cliente()
    if client is None:
        return
    ahora = datetime.now(timezone.utc).isoformat()
    client.table("panel_estado").upsert(
        {
            "id": 1,
            "payload": _json_safe(payload),
            "pc_en_linea": True,
            "impresora": _printer_name() or None,
            "updated_at": ahora,
        }
    ).execute()
    tablas = _filas_sqlite()
    if tablas["productos"]:
        client.table("productos").upsert(tablas["productos"]).execute()
    if tablas["caja"]:
        client.table("caja").upsert(tablas["caja"]).execute()
    if tablas["ventas"]:
        client.table("ventas").upsert(tablas["ventas"]).execute()


def procesar_pedidos_remotos() -> int:
    client = _cliente()
    if client is None:
        return 0
    res = (
        client.table("pedidos_remotos")
        .select("*")
        .eq("estado", "pendiente")
        .order("created_at")
        .limit(10)
        .execute()
    )
    procesados = 0
    for pedido in res.data or []:
        pid = pedido["id"]
        claim = (
            client.table("pedidos_remotos")
            .update({"estado": "procesando"})
            .eq("id", pid)
            .eq("estado", "pendiente")
            .execute()
        )
        if not claim.data:
            continue
        try:
            resultado = registrar_venta(
                pedido.get("items") or [],
                str(pedido.get("metodo_pago") or ""),
                pedido.get("recibido"),
                "Nube",
                True,
            )
            estado = "impreso" if resultado.get("impreso") else "registrado"
            client.table("pedidos_remotos").update(
                {
                    "estado": estado,
                    "factura": resultado.get("factura"),
                    "total": resultado.get("total"),
                    "error": resultado.get("error_impresion"),
                }
            ).eq("id", pid).execute()
            procesados += 1
        except VentaError as exc:
            client.table("pedidos_remotos").update(
                {"estado": "error", "error": exc.mensaje}
            ).eq("id", pid).execute()
        except Exception as exc:
            client.table("pedidos_remotos").update(
                {"estado": "error", "error": str(exc)[:300]}
            ).eq("id", pid).execute()
    return procesados


def ciclo_nube(obtener_payload) -> str:
    """Una pasada: atiende pedidos, sube estado si cambió. Devuelve mensaje corto."""
    if not nube_activa():
        return "nube desactivada"
    if not db_path().exists():
        return "sin base local"
    sync = _cargar_estado_sync()
    try:
        procesados = procesar_pedidos_remotos()
        try:
            sincronizar_usuarios_pos(sync)
        except Exception as exc:
            sync["ultimo_error_auth"] = str(exc)[:200]
        payload = obtener_payload()
        firma = str(payload.get("firma") or "")
        ahora_ts = time.time()
        if procesados or firma != sync.get("ultima_firma"):
            subir_estado(payload)
            sync["ultima_firma"] = firma
            sync["last_beat"] = ahora_ts
        elif ahora_ts - float(sync.get("last_beat") or 0) >= 8:
            client = _cliente()
            if client is not None:
                client.table("panel_estado").update(
                    {
                        "pc_en_linea": True,
                        "impresora": _printer_name() or None,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                ).eq("id", 1).execute()
            sync["last_beat"] = ahora_ts
        sync["ultimo_error"] = None
        _guardar_estado_sync(sync)
        return "ok" if not procesados else f"pedidos {procesados}"
    except Exception as exc:
        sync["ultimo_error"] = str(exc)[:400]
        _guardar_estado_sync(sync)
        return f"error: {exc}"


if __name__ == "__main__":
    estado = _cargar_estado_sync()
    estado.pop("firma_usuarios", None)
    estado["ultimo_error_auth"] = "forzar"
    sincronizar_usuarios_pos(estado)
    _guardar_estado_sync(estado)
    err = estado.get("ultimo_error_auth")
    print("SYNC_OK" if not err else f"SYNC_ERR {err}")
