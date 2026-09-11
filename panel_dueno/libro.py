"""Libro de ventas en Supabase: se agrega, no se borra, y se consulta por fechas."""

from __future__ import annotations

import hashlib
import re
from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Any

from snapshot import _connect, _rows, db_path

MESES = (
    "",
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)

_ISO_DIA = re.compile(r"(20\d{2})[-/](\d{2})[-/](\d{2})")
_LATINO_DIA = re.compile(r"(\d{2})[-/](\d{2})[-/](20\d{2})")


def parse_fecha_dia(texto: str | None) -> date | None:
    t = (texto or "").strip()
    if not t:
        return None
    t = t.replace("T", " ")
    cabeza = t[:10]
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(cabeza, fmt).date()
        except ValueError:
            continue
    m = _ISO_DIA.search(t)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    m = _LATINO_DIA.search(t)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass
    return None


def parse_fecha_hora(texto: str | None) -> str | None:
    t = (texto or "").strip().replace("T", " ")
    if not t:
        return None
    for fmt, ancho in (
        ("%Y-%m-%d %H:%M:%S", 19),
        ("%Y-%m-%d %H:%M", 16),
        ("%d/%m/%Y %H:%M:%S", 19),
        ("%d/%m/%Y %H:%M", 16),
    ):
        try:
            dt = datetime.strptime(t[:ancho], fmt)
            return dt.isoformat(timespec="seconds")
        except ValueError:
            continue
    dia = parse_fecha_dia(t)
    return f"{dia.isoformat()}T00:00:00" if dia else None


def clave_venta(fila: dict[str, Any], origen: str = "pos") -> str:
    partes = [
        origen,
        str(fila.get("id") or ""),
        str(fila.get("fecha") or ""),
        str(fila.get("producto_id") or ""),
        str(fila.get("nombre_producto") or ""),
        str(fila.get("cantidad") or ""),
        f"{float(fila.get('total') or 0):.2f}",
        str(fila.get("metodo_pago") or ""),
        str(fila.get("id_caja") or ""),
    ]
    return hashlib.sha256("|".join(partes).encode("utf-8")).hexdigest()


def fila_libro(crudo: dict[str, Any], origen: str = "pos") -> dict[str, Any] | None:
    dia = parse_fecha_dia(str(crudo.get("fecha") or crudo.get("fecha_texto") or ""))
    if dia is None:
        return None
    return {
        "clave_local": clave_venta(crudo, origen),
        "fecha_hora": parse_fecha_hora(str(crudo.get("fecha") or "")),
        "fecha_dia": dia.isoformat(),
        "fecha_texto": str(crudo.get("fecha") or ""),
        "producto_id": crudo.get("producto_id"),
        "nombre_producto": str(crudo.get("nombre_producto") or "Producto"),
        "cantidad": int(crudo.get("cantidad") or 0),
        "precio_unitario": float(crudo.get("precio_unitario") or 0),
        "total": float(crudo.get("total") or 0),
        "metodo_pago": str(crudo.get("metodo_pago") or ""),
        "id_caja": crudo.get("id_caja"),
        "nota": crudo.get("nota"),
        "origen": origen,
    }


def ventas_locales() -> list[dict[str, Any]]:
    path = db_path()
    if not path.exists():
        return []
    conn = _connect()
    try:
        filas = _rows(
            conn,
            """
            SELECT id, fecha, producto_id, nombre_producto, cantidad,
                   precio_unitario, total, metodo_pago, id_caja, nota
            FROM ventas
            ORDER BY id
            """,
        )
    except Exception:
        return []
    finally:
        conn.close()
    out = []
    for fila in filas:
        item = fila_libro(dict(fila), "pos")
        if item:
            out.append(item)
    return out


def rango_periodo(
    periodo: str,
    desde: str | None = None,
    hasta: str | None = None,
    hoy: date | None = None,
) -> tuple[date, date, str]:
    hoy = hoy or date.today()
    tipo = (periodo or "dia").strip().lower()
    if tipo in ("año", "ano", "anio", "year"):
        tipo = "anio"
    d1 = parse_fecha_dia(desde)
    d2 = parse_fecha_dia(hasta)

    if tipo == "semana":
        base = d1 or hoy
        inicio = base - timedelta(days=base.weekday())
        fin = inicio + timedelta(days=6)
        etiqueta = f"Semana del {inicio.day} al {fin.day} {MESES[fin.month]} {fin.year}"
        return inicio, fin, etiqueta
    if tipo == "mes":
        base = d1 or hoy
        inicio = date(base.year, base.month, 1)
        fin = date(base.year, base.month, monthrange(base.year, base.month)[1])
        etiqueta = f"{MESES[inicio.month].capitalize()} {inicio.year}"
        return inicio, fin, etiqueta
    if tipo == "anio":
        base = d1 or hoy
        inicio = date(base.year, 1, 1)
        fin = date(base.year, 12, 31)
        etiqueta = str(inicio.year)
        return inicio, fin, etiqueta
    if tipo == "rango":
        inicio = d1 or hoy
        fin = d2 or inicio
        if inicio > fin:
            inicio, fin = fin, inicio
        etiqueta = f"{inicio.isoformat()} → {fin.isoformat()}"
        return inicio, fin, etiqueta
    dia = d1 or hoy
    etiqueta = "Hoy" if dia == hoy else f"{dia.day} {MESES[dia.month]} {dia.year}"
    return dia, dia, etiqueta


def _resumen_filas(filas: list[dict[str, Any]], desde: date, hasta: date) -> dict[str, Any]:
    por_metodo: dict[str, float] = {}
    por_dia: dict[str, dict[str, Any]] = {}
    por_producto: dict[str, dict[str, Any]] = {}
    total = 0.0
    items = 0
    for fila in filas:
        dia = parse_fecha_dia(str(fila.get("fecha_dia") or fila.get("fecha") or ""))
        if dia is None or dia < desde or dia > hasta:
            continue
        monto = float(fila.get("total") or 0)
        cant = int(fila.get("cantidad") or 0)
        metodo = str(fila.get("metodo_pago") or "").strip() or "Sin método"
        nombre = str(fila.get("nombre_producto") or "Producto")
        total += monto
        items += cant
        por_metodo[metodo] = por_metodo.get(metodo, 0.0) + monto
        acc_dia = por_dia.setdefault(dia.isoformat(), {"fecha": dia.isoformat(), "total": 0.0, "items": 0, "lineas": 0})
        acc_dia["total"] += monto
        acc_dia["items"] += cant
        acc_dia["lineas"] += 1
        acc_prod = por_producto.setdefault(nombre, {"nombre": nombre, "cantidad": 0, "total": 0.0})
        acc_prod["cantidad"] += cant
        acc_prod["total"] += monto
    efectivo = float(por_metodo.get("Efectivo") or 0)
    return {
        "total": round(total, 2),
        "items": items,
        "lineas": sum(d["lineas"] for d in por_dia.values()),
        "efectivo": round(efectivo, 2),
        "otros_medios": round(total - efectivo, 2),
        "por_metodo": {k: round(v, 2) for k, v in sorted(por_metodo.items(), key=lambda x: -x[1])},
        "por_dia": [
            {**d, "total": round(d["total"], 2)}
            for d in sorted(por_dia.values(), key=lambda x: x["fecha"])
        ],
        "por_producto": [
            {**p, "total": round(p["total"], 2)}
            for p in sorted(por_producto.values(), key=lambda x: -x["total"])[:30]
        ],
    }


def _paginar(client, tabla: str, columnas: str = "*") -> list[dict[str, Any]]:
    filas: list[dict[str, Any]] = []
    inicio = 0
    tam = 1000
    while True:
        res = client.table(tabla).select(columnas).range(inicio, inicio + tam - 1).execute()
        lote = list(res.data or [])
        filas.extend(lote)
        if len(lote) < tam:
            break
        inicio += tam
        if inicio > 200_000:
            break
    return filas


def _subir_lotes(client, filas: list[dict[str, Any]]) -> int:
    enviadas = 0
    for i in range(0, len(filas), 200):
        lote = filas[i : i + 200]
        client.table("libro_ventas").upsert(
            lote,
            on_conflict="clave_local",
            ignore_duplicates=True,
        ).execute()
        enviadas += len(lote)
    return enviadas


def _migrar_ventas_viejas(client) -> int:
    try:
        viejas = _paginar(client, "ventas")
    except Exception:
        return 0
    if not viejas:
        return 0
    filas = []
    for crudo in viejas:
        item = fila_libro(crudo, "legacy")
        if item:
            filas.append(item)
    if not filas:
        return 0
    return _subir_lotes(client, filas)


def sincronizar_libro(client) -> dict[str, Any]:
    """Sube ventas locales al libro. Nunca borra filas de la nube."""
    if client is None:
        return {"ok": False, "error": "nube desactivada", "subidas": 0}
    locales = ventas_locales()
    try:
        _migrar_ventas_viejas(client)
        subidas = _subir_lotes(client, locales) if locales else 0
        return {"ok": True, "error": None, "locales": len(locales), "subidas": subidas}
    except Exception as exc:
        texto = str(exc)
        if "libro_ventas" in texto and ("schema cache" in texto or "does not exist" in texto or "PGRST" in texto):
            return {
                "ok": False,
                "error": "Falta crear la tabla libro_ventas. Ejecuta nube/supabase/schema.sql en Supabase.",
                "subidas": 0,
            }
        return {"ok": False, "error": texto[:400], "subidas": 0}


def reporte_desde_nube(client, desde: date, hasta: date) -> dict[str, Any] | None:
    if client is None:
        return None
    try:
        res = client.rpc(
            "reporte_ventas",
            {"p_desde": desde.isoformat(), "p_hasta": hasta.isoformat()},
        ).execute()
        data = res.data
        if isinstance(data, list) and data:
            data = data[0]
        if isinstance(data, dict) and "total" in data:
            data["fuente"] = "nube"
            return data
    except Exception:
        pass
    try:
        filas = []
        inicio = 0
        tam = 1000
        while True:
            res = (
                client.table("libro_ventas")
                .select("fecha_dia,nombre_producto,cantidad,total,metodo_pago")
                .gte("fecha_dia", desde.isoformat())
                .lte("fecha_dia", hasta.isoformat())
                .range(inicio, inicio + tam - 1)
                .execute()
            )
            lote = list(res.data or [])
            filas.extend(lote)
            if len(lote) < tam:
                break
            inicio += tam
        data = _resumen_filas(filas, desde, hasta)
        data["fuente"] = "nube"
        data["desde"] = desde.isoformat()
        data["hasta"] = hasta.isoformat()
        return data
    except Exception:
        return None


def reporte_desde_local(desde: date, hasta: date) -> dict[str, Any]:
    filas = ventas_locales()
    data = _resumen_filas(filas, desde, hasta)
    data["fuente"] = "local"
    data["desde"] = desde.isoformat()
    data["hasta"] = hasta.isoformat()
    return data


def armar_reporte(
    client,
    periodo: str = "dia",
    desde: str | None = None,
    hasta: str | None = None,
) -> dict[str, Any]:
    inicio, fin, etiqueta = rango_periodo(periodo, desde, hasta)
    nube = reporte_desde_nube(client, inicio, fin)
    local = reporte_desde_local(inicio, fin)
    if nube is None:
        elegido = local
        elegido["aviso"] = "Sin nube; este reporte sale del computador."
    else:
        elegido = nube
        if elegido.get("lineas") == 0 and local.get("lineas"):
            elegido = local
            elegido["aviso"] = "La nube aún no tiene esas ventas; se muestran las del computador."
        else:
            elegido["aviso"] = None
    elegido["periodo"] = periodo if periodo != "año" else "anio"
    elegido["etiqueta"] = etiqueta
    elegido["desde"] = inicio.isoformat()
    elegido["hasta"] = fin.isoformat()
    return elegido
