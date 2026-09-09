import sqlite3

conexion = sqlite3.connect("datos_pos.db")
cursor = conexion.cursor()

cursor.execute("SELECT * FROM usuarios")
usuarios = cursor.fetchall()

print("Usuarios registrados:")
for u in usuarios:
    print(u)

conexion.close()
