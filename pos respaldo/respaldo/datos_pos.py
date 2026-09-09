import sqlite3

conn = sqlite3.connect("datos_pos.db")  # Ajusta el nombre si es distinto
cur = conn.cursor()

cur.execute("PRAGMA table_info(fiados)")
for col in cur.fetchall():
    print(col)

conn.close()
