import sqlite3

conn = sqlite3.connect("datos_pos.db")
cursor = conn.cursor()

# Agregar columna monto_pagado si no existe
try:
    cursor.execute("ALTER TABLE fiados ADD COLUMN monto_pagado REAL DEFAULT 0")
    print("Columna monto_pagado agregada.")
except sqlite3.OperationalError:
    print("La columna monto_pagado ya existe.")

conn.commit()
conn.close()
