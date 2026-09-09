# reportes_impresion.py
"""Reportes de turno/sesión de caja. Fechas locales vía fechahora."""
import ast
import sqlite3
import fechahora as fh


def formatear_moneda(v):
    return f"${float(v or 0):,.2f}".replace(",", ".")


def obtener_totales(cursor, filtro_sql, params):
    cursor.execute(f"SELECT SUM(total) FROM ventas WHERE {filtro_sql}", params)
    total_general = cursor.fetchone()[0] or 0.0
    cursor.execute(
        f"""
        SELECT metodo_pago, SUM(total)
        FROM ventas
        WHERE {filtro_sql}
        GROUP BY metodo_pago
        """,
        params,
    )
    por_metodo = cursor.fetchall()
    return total_general, por_metodo


def _fetch_caja(cursor, id_caja=None, usuario=None):
    """Lee caja tolerando DBs antiguas sin columna fecha_cierre."""
    try:
        if id_caja:
            cursor.execute(
                """
                SELECT id, fecha, hora_apertura, fecha_cierre, hora_cierre,
                       capital_inicial, capital_final, total_ventas
                FROM caja WHERE id = ? LIMIT 1
                """,
                (id_caja,),
            )
        else:
            cursor.execute(
                """
                SELECT id, fecha, hora_apertura, fecha_cierre, hora_cierre,
                       capital_inicial, capital_final, total_ventas
                FROM caja
                WHERE usuario = ?
                ORDER BY CASE WHEN hora_cierre IS NULL THEN 0 ELSE 1 END, id DESC
                LIMIT 1
                """,
                (usuario,),
            )
        return cursor.fetchone(), True
    except sqlite3.OperationalError:
        if id_caja:
            cursor.execute(
                """
                SELECT id, fecha, hora_apertura, hora_cierre,
                       capital_inicial, capital_final, total_ventas
                FROM caja WHERE id = ? LIMIT 1
                """,
                (id_caja,),
            )
        else:
            cursor.execute(
                """
                SELECT id, fecha, hora_apertura, hora_cierre,
                       capital_inicial, capital_final, total_ventas
                FROM caja
                WHERE usuario = ?
                ORDER BY CASE WHEN hora_cierre IS NULL THEN 0 ELSE 1 END, id DESC
                LIMIT 1
                """,
                (usuario,),
            )
        row = cursor.fetchone()
        if not row:
            return None, False
        adapted = (row[0], row[1], row[2], None, row[3], row[4], row[5], row[6])
        return adapted, False


def obtener_sesion_caja(usuario, id_caja=None):
    conn = sqlite3.connect("datos_pos.db")
    cursor = conn.cursor()
    sesion, _ = _fetch_caja(cursor, id_caja=id_caja, usuario=usuario)
    conn.close()
    return sesion


def _parse_parcial(metodo: str):
    """Extrae dict de 'Pago parcial: {...}' si existe."""
    m = (metodo or "").strip()
    if not m.startswith("Pago parcial:"):
        return None
    try:
        return ast.literal_eval(m.split(":", 1)[1].strip())
    except Exception:
        return None


def _aportacion_metodos(metodo: str, total: float):
    """Descompone una línea de venta en aportes por método."""
    parcial = _parse_parcial(metodo)
    if parcial and isinstance(parcial, dict):
        # Solo la 1ª línea del ticket guarda el dict completo
        return {str(k): float(v or 0) for k, v in parcial.items() if float(v or 0) > 0}
    clave = (metodo or "Otro").strip() or "Otro"
    if clave == "Pago parcial":
        # Líneas siguientes: el total de venta ya suma, el medio ya se contó
        return {}
    return {clave: float(total or 0)}


def totales_por_sesion(cursor, id_caja: int):
    """Totales del turno (apertura→cierre) por método de pago."""
    cursor.execute(
        "SELECT metodo_pago, total FROM ventas WHERE id_caja = ?",
        (id_caja,),
    )
    filas = cursor.fetchall()
    total_general = 0.0
    agrupado = {}
    parciales_vistos = set()
    for metodo, subtotal in filas:
        total_general += float(subtotal or 0)
        m = (metodo or "").strip()
        # Evitar doble conteo histórico (mismo dict en varias líneas del ticket)
        if m.startswith("Pago parcial:"):
            if m in parciales_vistos:
                continue
            parciales_vistos.add(m)
        for clave, monto in _aportacion_metodos(metodo, subtotal).items():
            agrupado[clave] = agrupado.get(clave, 0.0) + float(monto)
    por_metodo = sorted(agrupado.items(), key=lambda x: (-x[1], x[0]))
    return float(total_general), por_metodo


def efectivo_del_turno(cursor, id_caja: int) -> float:
    """Efectivo físico que entró a caja en el turno (incluye parte de pagos parciales)."""
    _, por_metodo = totales_por_sesion(cursor, id_caja)
    efectivo = 0.0
    for metodo, subtotal in por_metodo:
        if str(metodo).lower().startswith("efectivo"):
            efectivo += float(subtotal)
    return efectivo


def armar_texto_reporte_diario(usuario, id_caja=None):
    """
    Reporte del TURNO de caja (desde apertura hasta cierre).
    Siempre ligado a id_caja — no al día calendario.
    """
    conn = sqlite3.connect("datos_pos.db")
    cursor = conn.cursor()

    caja, _has_fc = _fetch_caja(cursor, id_caja=id_caja, usuario=usuario)
    lines = []
    lines.append("===== REPORTE DE TURNO =====")
    lines.append(f"Usuario: {usuario}")
    lines.append(f"Impreso: {fh.datetime_sql()}")

    if not caja:
        lines.append("")
        lines.append("Sin sesion de caja.")
        lines.append("Abre caja para generar el reporte.")
        lines.append("=========================")
        conn.close()
        return "\n".join(lines)

    cid, fecha_ap, hora_ap, fecha_ci, hora_ci, capital_inicial, capital_final, _tv = caja
    total_general, por_metodo = totales_por_sesion(cursor, cid)
    efectivo = efectivo_del_turno(cursor, cid)

    lines.append(f"ID caja: {cid}")
    lines.append(f"Apertura: {fecha_ap} {hora_ap}")
    if hora_ci:
        cierre_txt = f"{(fecha_ci or fecha_ap)} {hora_ci}".strip()
        lines.append(f"Cierre:   {cierre_txt}")
    else:
        lines.append("Cierre:   (en curso)")
    lines.append("------------------------------")
    lines.append(f"Capital inicial: {formatear_moneda(capital_inicial)}")
    lines.append("")
    lines.append("Ingresos por metodo:")
    if not por_metodo:
        lines.append("  (sin ventas en este turno)")
    else:
        for metodo, subtotal in por_metodo:
            lines.append(f"  {metodo:<14}{formatear_moneda(subtotal)}")
    lines.append("------------------------------")
    lines.append(f"TOTAL VENTAS:   {formatear_moneda(total_general)}")
    lines.append(f"Efectivo turno: {formatear_moneda(efectivo)}")

    esperado_caja = float(capital_inicial or 0) + efectivo
    lines.append(f"Esperado en caja:{formatear_moneda(esperado_caja)}")
    if capital_final is not None:
        lines.append(f"Capital contado: {formatear_moneda(capital_final)}")
        diff = float(capital_final) - esperado_caja
        etiqueta = "Sobrante" if diff >= 0 else "Faltante"
        lines.append(f"{etiqueta}:       {formatear_moneda(abs(diff))}")
    lines.append("=========================")
    lines.append("(Totales = desde apertura")
    lines.append(" hasta cierre de esta caja)")

    conn.close()
    return "\n".join(lines)


def armar_texto_reporte_mensual(usuario, año_mes):
    conn = sqlite3.connect("datos_pos.db")
    cursor = conn.cursor()

    filtro = "strftime('%Y-%m', fecha) = ?"
    total_general, por_metodo = obtener_totales(cursor, filtro, (año_mes,))

    lines = []
    lines.append("==== REPORTE MENSUAL ====")
    lines.append(f"Usuario: {usuario}")
    lines.append(f"Mes: {año_mes}")
    lines.append(f"Impreso: {fh.datetime_sql()}")
    lines.append("")
    lines.append(f"Total general: {formatear_moneda(total_general)}")
    lines.append("")
    lines.append("Por método de pago:")
    for metodo, subtotal in por_metodo:
        lines.append(f"{metodo:<12}{formatear_moneda(subtotal)}")
    lines.append("=========================")

    conn.close()
    return "\n".join(lines)


def armar_texto_reporte_rango(usuario, inicio, fin):
    conn = sqlite3.connect("datos_pos.db")
    cursor = conn.cursor()

    filtro = "substr(fecha,1,10) BETWEEN ? AND ?"
    total_general, por_metodo = obtener_totales(cursor, filtro, (inicio, fin))

    lines = []
    lines.append("=== REPORTE POR RANGO ===")
    lines.append(f"Usuario: {usuario}")
    lines.append(f"Desde: {inicio}")
    lines.append(f"Hasta: {fin}")
    lines.append(f"Impreso: {fh.datetime_sql()}")
    lines.append("")
    lines.append(f"Total general: {formatear_moneda(total_general)}")
    lines.append("")
    lines.append("Por método de pago:")
    for metodo, subtotal in por_metodo:
        lines.append(f"{metodo:<12}{formatear_moneda(subtotal)}")
    lines.append("=========================")

    conn.close()
    return "\n".join(lines)


def imprimir_texto(texto):
    from impresion import enviar_a_impresora

    enviar_a_impresora(texto)
