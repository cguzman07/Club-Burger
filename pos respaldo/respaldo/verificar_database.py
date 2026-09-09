import sqlite3
conn = sqlite3.connect("datos_pos.db")
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(caja);")
print(cursor.fetchall())
conn.close()
