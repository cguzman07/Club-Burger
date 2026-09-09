import sqlite3
import threading
import os
import hashlib
import binascii
from typing import Optional

DB_PATH = "datos_pos.db"
_LOCK = threading.Lock()

def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return binascii.hexlify(salt + dk).decode("ascii")

def verify_password(stored: str, provided: str) -> bool:
    data = binascii.unhexlify(stored.encode("ascii"))
    salt, stored_dk = data[:16], data[16:]
    new_dk = hashlib.pbkdf2_hmac("sha256", provided.encode("utf-8"), salt, 100_000)
    return hmac_compare(stored_dk, new_dk)

def hmac_compare(a: bytes, b: bytes) -> bool:
    return len(a) == len(b) and all(x == y for x, y in zip(a, b))

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
                hashed = hash_password("admin")
                cur.execute(
                    "INSERT INTO usuarios (usuario, contrasena, rol) VALUES (?, ?, ?)",
                    ("admin", hashed, "admin")
                )

            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

def obtener_usuario_para_login(usuario: str, contrasena: str):
    row = consultar_uno("SELECT id, usuario, contrasena, rol FROM usuarios WHERE usuario = ? LIMIT 1;", (usuario,))
    if row and verify_password(row["contrasena"], contrasena):
        return {"id": row["id"], "usuario": row["usuario"], "rol": row["rol"]}
    return None

def listar_categorias():
    return consultar_todos("SELECT nombre FROM categorias ORDER BY nombre;")

def agregar_categoria(nombre: str):
    ejecutar("INSERT OR IGNORE INTO categorias (nombre) VALUES (?);", (nombre,))
