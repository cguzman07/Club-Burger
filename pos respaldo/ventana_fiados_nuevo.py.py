import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from database import ejecutar

def abrir_ventana_nuevo_fiado(ventana_padre, refrescar_func=None):
    ventana_fiado = tk.Toplevel(ventana_padre)
    ventana_fiado.title("Nuevo Fiado")
    ventana_fiado.geometry("300x200")
    ventana_fiado.resizable(False, False)

    tk.Label(ventana_fiado, text="Nombre:").pack(pady=5)
    entrada_nombre = tk.Entry(ventana_fiado)
    entrada_nombre.pack(pady=5)

    tk.Label(ventana_fiado, text="Monto pendiente:").pack(pady=5)
    entrada_monto = tk.Entry(ventana_fiado)
    entrada_monto.pack(pady=5)

    def guardar_fiado():
        nombre = entrada_nombre.get().strip()
        try:
            monto = float(entrada_monto.get())
        except ValueError:
            messagebox.showerror("Error", "Monto inválido")
            return

        if not nombre:
            messagebox.showerror("Error", "Debe ingresar un nombre")
            return

        # Insertar en tabla fiados
        ejecutar(
            "INSERT INTO fiados (cliente, fecha, monto_total, monto_pagado) VALUES (?, ?, ?, ?)",
            (nombre, datetime.now().strftime("%Y-%m-%d"), monto, 0.0)
        )
        messagebox.showinfo("Guardado", f"Fiado guardado para {nombre}")

        if refrescar_func:
            refrescar_func()

        ventana_fiado.destroy()

    tk.Button(ventana_fiado, text="Guardar", command=guardar_fiado).pack(pady=10)
