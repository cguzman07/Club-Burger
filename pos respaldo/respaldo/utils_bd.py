from datetime import datetime
from database import get_connection, ejecutar, consultar_todos

def guardar_venta(fecha: str, producto_id: int, nombre_producto: str, cantidad: int,
                  precio_unitario: float, total: float, metodo_pago: str, id_caja: int | None):
    """
    Inserta una venta usando el esquema completo de la tabla 'ventas' definida en database.py.
    Se asume que la tabla ya existe (inicializada por inicializar_db()).
    """
    query = '''
        INSERT INTO ventas (
            fecha, producto_id, nombre_producto, cantidad,
            precio_unitario, total, metodo_pago, id_caja
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    '''
    ejecutar(query, (
        fecha,
        producto_id,
        nombre_producto,
        cantidad,
        precio_unitario,
        total,
        metodo_pago,
        id_caja
    ))

def obtener_ventas_por_fecha(fecha: str):
    # Filtra por fecha completa (YYYY-MM-DD) usando DATE()
    query = '''
        SELECT fecha, nombre_producto, cantidad, total, metodo_pago
        FROM ventas
        WHERE DATE(fecha) = ?
        ORDER BY fecha ASC
    '''
    return consultar_todos(query, (fecha,))

def obtener_ventas_por_mes(mes: int, anio: int):
    # Formatea como YYYY-MM y usa strftime para coincidir
    filtro = f"{anio}-{str(mes).zfill(2)}"
    query = '''
        SELECT fecha, nombre_producto, cantidad, total, metodo_pago
        FROM ventas
        WHERE strftime('%Y-%m', fecha) = ?
        ORDER BY fecha ASC
    '''
    return consultar_todos(query, (filtro,))

def obtener_ventas_por_rango(fecha_inicio: str, fecha_fin: str):
    query = '''
        SELECT fecha, nombre_producto, cantidad, total, metodo_pago
        FROM ventas
        WHERE DATE(fecha) BETWEEN ? AND ?
        ORDER BY fecha ASC
    '''
    return consultar_todos(query, (fecha_inicio, fecha_fin))
