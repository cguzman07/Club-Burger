"""Lectura de solo consulta de datos_pos.db. Nunca escribe en la caja."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

MESES = (
    "",
    "ene",
    "feb",
    "mar",
    "abr",
    "may",
    "jun",
    "jul",
    "ago",
    "sep",
    "oct",
    "nov",
    "dic",
)


def db_path() -> Path:
    return Path(__file__).resolve().parent.parent / "datos_pos.db"


def _connect() -> sqlite3.Connection:
    path = db_path()
    if not path.exists():
        raise FileNotFoundError(f"No se encontró {path}")
    uri = path.as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=8)
    conn.row_factory = sqlite3.Row
    return conn


def _rows(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    return list(conn.execute(sql, params))


def _es_vacio(valor: Any) -> bool:
    return valor is None or str(valor).strip() == ""


def _fmt_fecha(fecha: str | None, hora: str | None = None) -> str:
    if not fecha:
        return "—"
    try:
        if " " in fecha:
            dt = datetime.strptime(fecha[:19], "%Y-%m-%d %H:%M:%S")
            return f"{dt.day} {MESES[dt.month]} {dt.strftime('%H:%M')}"
        d = datetime.strptime(fecha[:10], "%Y-%m-%d")
        if hora:
            h = hora[:5]
            return f"{d.day} {MESES[d.month]}, {h}"
        return f"{d.day} {MESES[d.month]} {d.year}"
    except ValueError:
        return fecha


def _agregar_metodos(filas: list[sqlite3.Row]) -> dict[str, float]:
    out: dict[str, float] = {}
    for fila in filas:
        metodo = (fila["metodo_pago"] or "Sin método").strip() or "Sin método"
        out[metodo] = out.get(metodo, 0.0) + float(fila["total"] or 0)
    return dict(sorted(out.items(), key=lambda item: item[1], reverse=True))


def _nivel_stock(stock: int, inicial: int, umbral: int) -> str:
    if stock <= 0:
        return "agotado"
    if stock <= umbral:
        return "bajo"
    if inicial >= 10 and stock / inicial <= 0.2:
        return "bajo"
    return "ok"


def _inventario(conn: sqlite3.Connection, ventas_hoy: list[sqlite3.Row], umbral: int) -> dict[str, Any]:
    vendido_hoy: dict[int, int] = {}
    for venta in ventas_hoy:
        pid = venta["producto_id"]
        if pid is None:
            continue
        vendido_hoy[int(pid)] = vendido_hoy.get(int(pid), 0) + int(venta["cantidad"] or 0)

    productos = []
    firma_partes = []
    for fila in _rows(conn, "SELECT * FROM productos ORDER BY categoria, nombre"):
        stock = int(fila["stock"] or 0)
        inicial = int(fila["stock_inicial"] or 0)
        nivel = _nivel_stock(stock, inicial, umbral)
        pct = round(100 * stock / inicial) if inicial > 0 else None
        pid = int(fila["id"])
        productos.append(
            {
                "id": pid,
                "nombre": fila["nombre"] or "Producto",
                "categoria": (fila["categoria"] or "Sin categoría").strip() or "Sin categoría",
                "precio": float(fila["precio"] or 0),
                "stock": stock,
                "stock_inicial": inicial,
                "porcentaje": pct,
                "nivel": nivel,
                "vendido_hoy": vendido_hoy.get(pid, 0),
            }
        )
        firma_partes.append(f"{pid}:{stock}")

    orden = {"agotado": 0, "bajo": 1, "ok": 2}
    productos.sort(key=lambda p: (orden[p["nivel"]], p["categoria"].lower(), p["nombre"].lower()))
    categorias = sorted({p["categoria"] for p in productos})
    agotados = sum(1 for p in productos if p["nivel"] == "agotado")
    bajos = sum(1 for p in productos if p["nivel"] == "bajo")
    return {
        "umbral": umbral,
        "total": len(productos),
        "agotados": agotados,
        "bajos": bajos,
        "ok": len(productos) - agotados - bajos,
        "atencion": agotados + bajos,
        "categorias": categorias,
        "productos": productos,
        "firma": ",".join(firma_partes) or "0",
    }


def _resumen_ventas(filas: list[sqlite3.Row]) -> dict[str, Any]:
    total = sum(float(f["total"] or 0) for f in filas)
    items = sum(int(f["cantidad"] or 0) for f in filas)
    return {
        "total": round(total, 2),
        "items": items,
        "lineas": len(filas),
        "por_metodo": _agregar_metodos(filas),
    }


def leer_estado(umbral: int = 5) -> dict[str, Any]:
    path = db_path()
    if not path.exists():
        return {
            "ok": False,
            "error": "No se encontró datos_pos.db. Abre Club Burger en este mismo computador.",
            "firma": "sin-db",
        }

    hoy = date.today().isoformat()
    conn = _connect()
    try:
        cajas = _rows(conn, "SELECT * FROM caja ORDER BY id DESC")
        caja_abierta = next((c for c in cajas if _es_vacio(c["hora_cierre"])), None)
        caja_ref = caja_abierta or (cajas[0] if cajas else None)

        ventas_todas = _rows(
            conn,
            """
            SELECT id, fecha, producto_id, nombre_producto, cantidad, precio_unitario, total, metodo_pago, id_caja, nota
            FROM ventas
            ORDER BY id DESC
            """,
        )

        ventas_caja: list[sqlite3.Row] = []
        if caja_ref is not None:
            ventas_caja = [v for v in ventas_todas if v["id_caja"] == caja_ref["id"]]

        ventas_hoy = [v for v in ventas_todas if (v["fecha"] or "").startswith(hoy)]

        top: dict[str, dict[str, Any]] = {}
        fuente_top = ventas_caja if caja_abierta is not None else ventas_hoy
        for v in fuente_top:
            nombre = v["nombre_producto"] or "Producto"
            acc = top.setdefault(nombre, {"nombre": nombre, "cantidad": 0, "total": 0.0})
            acc["cantidad"] += int(v["cantidad"] or 0)
            acc["total"] += float(v["total"] or 0)
        top_lista = sorted(top.values(), key=lambda x: x["total"], reverse=True)[:5]
        for item in top_lista:
            item["total"] = round(item["total"], 2)

        ultimas = []
        for v in ventas_todas[:25]:
            ultimas.append(
                {
                    "id": v["id"],
                    "fecha": v["fecha"],
                    "fecha_corta": _fmt_fecha(v["fecha"]),
                    "producto": v["nombre_producto"],
                    "cantidad": int(v["cantidad"] or 0),
                    "total": round(float(v["total"] or 0), 2),
                    "metodo": (v["metodo_pago"] or "—").strip() or "—",
                    "nota": v["nota"],
                }
            )

        inventario = _inventario(conn, ventas_hoy, max(0, int(umbral)))
        max_venta = ventas_todas[0]["id"] if ventas_todas else 0
        max_caja = cajas[0]["id"] if cajas else 0
        cierre = "" if caja_abierta is not None else (caja_ref["hora_cierre"] if caja_ref else "none")
        firma = f"{max_venta}:{max_caja}:{cierre}:{len(ventas_todas)}:{hoy}:{inventario['firma']}"

        caja_payload = None
        if caja_ref is not None:
            caja_payload = {
                "id": caja_ref["id"],
                "abierta": caja_abierta is not None,
                "usuario": caja_ref["usuario"] or "—",
                "fecha": caja_ref["fecha"],
                "hora_apertura": caja_ref["hora_apertura"],
                "desde": _fmt_fecha(caja_ref["fecha"], caja_ref["hora_apertura"]),
                "hora_cierre": caja_ref["hora_cierre"],
                "fecha_cierre": caja_ref["fecha_cierre"],
                "capital_inicial": float(caja_ref["capital_inicial"] or 0),
                "capital_final": None
                if _es_vacio(caja_ref["capital_final"])
                else float(caja_ref["capital_final"]),
                "total_ventas_cierre": None
                if _es_vacio(caja_ref["total_ventas"])
                else float(caja_ref["total_ventas"]),
            }

        return {
            "ok": True,
            "error": None,
            "firma": firma,
            "ahora": datetime.now().strftime("%H:%M:%S"),
            "hoy": hoy,
            "caja": caja_payload,
            "atendiendo": caja_payload["usuario"] if caja_payload and caja_payload["abierta"] else None,
            "ventas_caja": _resumen_ventas(ventas_caja),
            "ventas_hoy": _resumen_ventas(ventas_hoy),
            "top_productos": top_lista,
            "ultimas_ventas": ultimas,
            "inventario": inventario,
        }
    finally:
        conn.close()
