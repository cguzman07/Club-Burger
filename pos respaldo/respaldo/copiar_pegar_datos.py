import sqlite3

# Archivos de base de datos
db_viejo = "datos_pos_viejo.db"
db_nuevo = "datos_pos.db"

# Conectar a ambas bases
conn_viejo = sqlite3.connect(db_viejo)
cursor_viejo = conn_viejo.cursor()

conn_nuevo = sqlite3.connect(db_nuevo)
cursor_nuevo = conn_nuevo.cursor()

# Leer todos los productos con stock_inicial
cursor_viejo.execute("SELECT nombre, categoria, precio, stock, stock_inicial FROM productos")
productos = cursor_viejo.fetchall()

print(f"Se encontraron {len(productos)} productos para transferir...")

# Insertar productos en la nueva base
for producto in productos:
    nombre, categoria, precio, stock, stock_inicial = producto
    cursor_nuevo.execute(
        "INSERT INTO productos (nombre, categoria, precio, stock, stock_inicial) VALUES (?, ?, ?, ?, ?)",
        (nombre, categoria, precio, stock, stock_inicial)
    )

# Guardar y cerrar
conn_nuevo.commit()
conn_viejo.close()
conn_nuevo.close()

print("Transferencia completada con éxito ✅")
