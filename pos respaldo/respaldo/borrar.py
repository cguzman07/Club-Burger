import sqlite3

def borrar_todos_fiados():
    conn = sqlite3.connect("datos_pos.db")
    cursor = conn.cursor()
    try:
        # Primero borrar pagos ligados a fiados (para no dejar referencias colgando)
        cursor.execute("DELETE FROM pagos_fiados")
        # Luego borrar todos los fiados
        cursor.execute("DELETE FROM fiados")
        conn.commit()
        print("✅ Todos los registros de fiados y pagos_fiados fueron eliminados.")
    except Exception as e:
        print("❌ Error al borrar:", e)
        conn.rollback()
    finally:
        conn.close()


# Ejecutar la función
if __name__ == "__main__":
    borrar_todos_fiados()
