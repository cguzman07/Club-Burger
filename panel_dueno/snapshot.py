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

METODOS_CAJA = ("Efectivo", "Nequi", "Daviplata", "Transferencia", "Tarjeta")


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


def _caja_sesion_vigente(caja: sqlite3.Row | None, hoy: str) -> bool:
    """Caja abierta de verdad: sin cierre y del turno actual (hoy o ayer)."""
    if caja is None or not _es_vacio(caja["hora_cierre"]):
        return False
    fecha = str(caja["fecha"] or "")[:10]
    if not fecha:
        return False
    try:
        dia = datetime.strptime(fecha, "%Y-%m-%d").date()
        actual = datetime.strptime(hoy, "%Y-%m-%d").date()
    except ValueError:
        return False
    return (actual - dia).days <= 1


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


def _agregar_metodos(filas: list[sqlite3.Row], completar: bool = True) -> dict[str, float]:
    out: dict[str, float] = {m: 0.0 for m in METODOS_CAJA} if completar else {}
    for fila in filas:
        metodo = (fila["metodo_pago"] or "Sin método").strip() or "Sin método"
        out[metodo] = out.get(metodo, 0.0) + float(fila["total"] or 0)
    orden = {nombre: i for i, nombre in enumerate(METODOS_CAJA)}
    return dict(
        sorted(
            ((k, round(v, 2)) for k, v in out.items()),
            key=lambda item: (orden.get(item[0], 99), -item[1], item[0]),
        )
    )


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
    por_metodo = _agregar_metodos(filas)
    efectivo = float(por_metodo.get("Efectivo") or 0)
    digitales = round(total - efectivo, 2)
    return {
        "total": round(total, 2),
        "items": items,
        "lineas": len(filas),
        "por_metodo": por_metodo,
        "efectivo": round(efectivo, 2),
        "otros_medios": digitales,
    }


def _fiados_dia(conn: sqlite3.Connection, dia: str) -> dict[str, Any]:
    vacio = {
        "nuevos": 0,
        "monto_nuevo": 0.0,
        "pagos": 0,
        "monto_pagado": 0.0,
        "pendiente": 0.0,
    }
    try:
        nuevos = _rows(conn, "SELECT * FROM fiados WHERE substr(COALESCE(fecha,''), 1, 10) = ?", (dia,))
        pagos = _rows(conn, "SELECT * FROM pagos_fiados WHERE substr(COALESCE(fecha,''), 1, 10) = ?", (dia,))
        pendientes = _rows(conn, "SELECT COALESCE(SUM(monto_pendiente), 0) AS t FROM fiados")
    except sqlite3.Error:
        return vacio
    return {
        "nuevos": len(nuevos),
        "monto_nuevo": round(sum(float(f["monto_pendiente"] or 0) for f in nuevos), 2) if nuevos else 0.0,
        "pagos": len(pagos),
        "monto_pagado": round(sum(float(p["monto_pagado"] or 0) for p in pagos), 2) if pagos else 0.0,
        "pendiente": round(float(pendientes[0]["t"] if pendientes else 0), 2),
    }


def _sesion_caja(caja: sqlite3.Row, ventas_caja: list[sqlite3.Row]) -> dict[str, Any]:
    resumen = _resumen_ventas(ventas_caja)
    capital = float(caja["capital_inicial"] or 0)
    abierto = _es_vacio(caja["hora_cierre"])
    capital_final = None if _es_vacio(caja["capital_final"]) else float(caja["capital_final"])
    total_pos = None if _es_vacio(caja["total_ventas"]) else float(caja["total_ventas"])
    esperado = round(capital + resumen["efectivo"], 2)
    ventas_cuadran = total_pos is None or abs(total_pos - resumen["total"]) < 0.01
    diferencia_efectivo = None if capital_final is None else round(capital_final - esperado, 2)
    return {
        "id": caja["id"],
        "usuario": caja["usuario"] or "—",
        "abierta": abierto,
        "fecha": caja["fecha"],
        "desde": _fmt_fecha(caja["fecha"], caja["hora_apertura"]),
        "hora_apertura": caja["hora_apertura"],
        "hora_cierre": caja["hora_cierre"],
        "fecha_cierre": caja["fecha_cierre"],
        "capital_inicial": capital,
        "capital_final": capital_final,
        "total_pos": total_pos,
        "ventas": resumen,
        "efectivo_esperado": esperado,
        "diferencia_efectivo": diferencia_efectivo,
        "ventas_cuadran": ventas_cuadran,
        "alerta": None
        if ventas_cuadran
        else "El total guardado al cerrar no coincide con la suma de las ventas.",
    }


def _reporte_diario(
    conn: sqlite3.Connection,
    cajas: list[sqlite3.Row],
    ventas_todas: list[sqlite3.Row],
    hoy: str,
) -> dict[str, Any]:
    por_caja: dict[int, list[sqlite3.Row]] = {}
    dias: set[str] = {hoy}
    for venta in ventas_todas:
        dia = (venta["fecha"] or "")[:10]
        if dia:
            dias.add(dia)
        cid = venta["id_caja"]
        if cid is not None:
            por_caja.setdefault(int(cid), []).append(venta)
    for caja in cajas:
        dia = (caja["fecha"] or "")[:10]
        if dia:
            dias.add(dia)

    lista = []
    for dia in sorted(dias, reverse=True)[:31]:
        ventas_dia = [v for v in ventas_todas if (v["fecha"] or "").startswith(dia)]
        resumen = _resumen_ventas(ventas_dia)
        ids_sesion = {int(c["id"]) for c in cajas if (c["fecha"] or "")[:10] == dia}
        for venta in ventas_dia:
            if venta["id_caja"] is not None:
                ids_sesion.add(int(venta["id_caja"]))
        sesiones = []
        for caja in sorted(cajas, key=lambda c: int(c["id"])):
            if int(caja["id"]) not in ids_sesion:
                continue
            sesiones.append(_sesion_caja(caja, por_caja.get(int(caja["id"]), [])))
        lista.append(
            {
                "fecha": dia,
                "etiqueta": _fmt_fecha(dia),
                "es_hoy": dia == hoy,
                "ventas": resumen,
                "sesiones": sesiones,
                "fiados": _fiados_dia(conn, dia),
            }
        )

    hoy_rep = next((d for d in lista if d["fecha"] == hoy), None)
    if hoy_rep is None:
        hoy_rep = {
            "fecha": hoy,
            "etiqueta": _fmt_fecha(hoy),
            "es_hoy": True,
            "ventas": _resumen_ventas([]),
            "sesiones": [],
            "fiados": _fiados_dia(conn, hoy),
        }
        lista.insert(0, hoy_rep)
    return {"hoy": hoy_rep, "dias": lista}


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
        caja_abierta = next((c for c in cajas if _caja_sesion_vigente(c, hoy)), None)
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
            "reporte": _reporte_diario(conn, cajas, ventas_todas, hoy),
        }
    finally:
        conn.close()
