import sqlite3
import threading
import os
import hashlib
import binascii
from typing import Optional

DB_PATH = "datos_pos.db"
_LOCK = threading.Lock()

# ---------- Conexión ----------
def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=5, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def ejecutar(query: str, params=(), commit: bool = True):
    with _LOCK:
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(query, params)
            if commit:
                conn.commit()
            return cur
        except Exception:
            conn.rollback()
            raise
        finally:
            if commit:
                conn.close()

def consultar_uno(query: str, params=()):
    with _LOCK:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query, params)
            return cur.fetchone()
        finally:
            conn.close()

def consultar_todos(query: str, params=()):
    with _LOCK:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query, params)
            return cur.fetchall()
        finally:
            conn.close()

def inicializar_db():
    with _LOCK:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario TEXT UNIQUE NOT NULL,
                    contrasena TEXT NOT NULL,
                    rol TEXT NOT NULL
                );
            ''')

            cur.execute('''
                CREATE TABLE IF NOT EXISTS categorias (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT UNIQUE NOT NULL
                );
            ''')

            cur.execute('''
                CREATE TABLE IF NOT EXISTS productos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    categoria TEXT NOT NULL,
                    precio REAL NOT NULL,
                    stock INTEGER NOT NULL,
                    stock_inicial INTEGER NOT NULL,
                    FOREIGN KEY(categoria) REFERENCES categorias(nombre) ON UPDATE CASCADE
                );
            ''')

            cur.execute('''
                CREATE TABLE IF NOT EXISTS caja (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario TEXT NOT NULL,
                    fecha TEXT NOT NULL,
                    hora_apertura TEXT NOT NULL,
                    capital_inicial REAL NOT NULL,
                    detalle_capital TEXT NOT NULL,
                    hora_cierre TEXT,
                    capital_final REAL,
                    total_ventas REAL
                );
            ''')

            cur.execute('''
                CREATE TABLE IF NOT EXISTS ventas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha TEXT NOT NULL,
                    producto_id INTEGER NOT NULL,
                    nombre_producto TEXT NOT NULL,
                    cantidad INTEGER NOT NULL,
                    precio_unitario REAL NOT NULL,
                    total REAL NOT NULL,
                    metodo_pago TEXT NOT NULL,
                    id_caja INTEGER,
                    FOREIGN KEY(producto_id) REFERENCES productos(id),
                    FOREIGN KEY(id_caja) REFERENCES caja(id)
                );
            ''')

            # Crear usuario admin si no existe
            cur.execute("SELECT * FROM usuarios WHERE usuario = ?", ("admin",))
            if not cur.fetchone():
                clave = ("admin")
                cur.execute(
                    "INSERT INTO usuarios (usuario, contrasena, rol) VALUES (?, ?, ?)",
                    ("admin", clave, "admin")
                )

            # --- Nuevas tablas para fiados y pagos ---
            cur.execute('''
                CREATE TABLE IF NOT EXISTS fiados (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre_cliente TEXT NOT NULL,
                    monto_pendiente REAL NOT NULL,
                    fecha TEXT NOT NULL DEFAULT (DATE('now','localtime'))
                );
            ''')

            cur.execute('''
                CREATE TABLE IF NOT EXISTS pagos_fiados (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fiado_id INTEGER NOT NULL,
                    monto_pagado REAL NOT NULL,
                    fecha TEXT NOT NULL DEFAULT (DATE('now','localtime')),
                    FOREIGN KEY (fiado_id) REFERENCES fiados(id) ON DELETE CASCADE
                );
            ''')

            # Columna para cierre después de medianoche (sesión continua)
            try:
                cur.execute("ALTER TABLE caja ADD COLUMN fecha_cierre TEXT;")
            except Exception:
                pass

            # Nota / descripción corta por línea de venta (sin salsa, sin queso, etc.)
            try:
                cur.execute("ALTER TABLE ventas ADD COLUMN nota TEXT;")
            except Exception:
                pass

            # Facturas en espera (cliente aún no paga)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS facturas_espera (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario TEXT NOT NULL,
                    etiqueta TEXT NOT NULL,
                    contenido TEXT NOT NULL,
                    total REAL NOT NULL DEFAULT 0,
                    creado TEXT NOT NULL
                );
                """
            )

            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

# ---------- Gestión de usuarios ----------
def obtener_usuario_para_login(usuario: str, contrasena: str):
    row = consultar_uno(
        "SELECT id, usuario, contrasena, rol FROM usuarios WHERE usuario = ? AND contrasena = ? LIMIT 1;",
        (usuario, contrasena)
    )
    if row:
        return {"id": row["id"], "usuario": row["usuario"], "rol": row["rol"]}
    return None

def agregar_usuario(usuario: str, contrasena: str, rol: str):
    ejecutar(
        "INSERT INTO usuarios (usuario, contrasena, rol) VALUES (?, ?, ?)",
        (usuario, contrasena, rol)
    )

def actualizar_contrasena(usuario: str, nueva_contrasena: str):
    ejecutar(
        "UPDATE usuarios SET contrasena = ? WHERE usuario = ?",
        (nueva_contrasena, usuario)
    )

def listar_categorias():
    return consultar_todos("SELECT nombre FROM categorias ORDER BY nombre;")

def agregar_categoria(nombre: str):
    ejecutar("INSERT OR IGNORE INTO categorias (nombre) VALUES (?);", (nombre,))

# --- Funciones para fiados y pagos ---

def registrar_fiado(nombre_cliente: str, monto_pendiente: float):
    query = "INSERT INTO fiados (nombre_cliente, monto_pendiente) VALUES (?, ?);"
    ejecutar(query, (nombre_cliente, monto_pendiente))

def registrar_pago_fiado(fiado_id: int, monto_pagado: float):
    with _LOCK:
        conn = get_connection()
        try:
            cur = conn.cursor()
            # Insertar el pago
            cur.execute(
                "INSERT INTO pagos_fiados (fiado_id, monto_pagado) VALUES (?, ?);",
                (fiado_id, monto_pagado)
            )
            # Actualizar monto pendiente en fiados
            cur.execute(
                "UPDATE fiados SET monto_pendiente = monto_pendiente - ? WHERE id = ?;",
                (monto_pagado, fiado_id)
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

def obtener_fiados_pendientes():
    """
    Retorna lista de diccionarios con:
    id, nombre_cliente, monto_pendiente, total_abonos
    """
    with _LOCK:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute('''
                SELECT
                    f.id,
                    f.nombre_cliente,
                    f.monto_pendiente,
                    IFNULL(SUM(p.monto_pagado), 0) AS total_abonos
                FROM fiados f
                LEFT JOIN pagos_fiados p ON f.id = p.fiado_id
                WHERE f.monto_pendiente > 0
                GROUP BY f.id
                ORDER BY f.nombre_cliente;
            ''')
            filas = cur.fetchall()
            return [dict(row) for row in filas]
        finally:
            conn.close()


# ---------- Sesión de caja (independiente de medianoche) ----------
def obtener_caja_abierta(usuario: str):
    """
    Devuelve la sesión de caja abierta del usuario, sin filtrar por fecha del día.
    Así el turno puede cruzar las 12:00 a.m. sin forzar nueva apertura.
    """
    return consultar_uno(
        """
        SELECT id, usuario, fecha, hora_apertura, capital_inicial, detalle_capital,
               hora_cierre, capital_final, total_ventas
        FROM caja
        WHERE usuario = ? AND hora_cierre IS NULL
        ORDER BY id DESC
        LIMIT 1
        """,
        (usuario,),
    )


def obtener_caja_por_id(id_caja: int):
    return consultar_uno("SELECT * FROM caja WHERE id = ? LIMIT 1", (id_caja,))


# ---------- Facturas en espera ----------
def guardar_factura_espera(usuario: str, etiqueta: str, contenido: str, total: float):
    import fechahora as fh

    ejecutar(
        """
        INSERT INTO facturas_espera (usuario, etiqueta, contenido, total, creado)
        VALUES (?, ?, ?, ?, ?)
        """,
        (usuario, etiqueta, contenido, float(total or 0), fh.datetime_sql()),
    )


def listar_facturas_espera(usuario: str):
    return consultar_todos(
        """
        SELECT id, etiqueta, contenido, total, creado
        FROM facturas_espera
        WHERE usuario = ?
        ORDER BY id DESC
        """,
        (usuario,),
    )


def obtener_factura_espera(id_espera: int):
    return consultar_uno(
        "SELECT id, usuario, etiqueta, contenido, total, creado FROM facturas_espera WHERE id = ? LIMIT 1",
        (id_espera,),
    )


def eliminar_factura_espera(id_espera: int):
    ejecutar("DELETE FROM facturas_espera WHERE id = ?", (id_espera,))
