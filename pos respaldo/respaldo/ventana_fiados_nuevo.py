from datetime import datetime
from tkinter import messagebox
import customtkinter as ctk

from database import ejecutar
import tema_caja as tema
import responsive as resp
import animaciones as anim
import fechahora as fh
import fondos


def abrir_ventana_nuevo_fiado(ventana_padre, refrescar_func=None):
    tema.apply_theme()

    ventana_fiado = ctk.CTkToplevel(ventana_padre)
    ventana_fiado.title("Nuevo Fiado")
    ventana_fiado.configure(fg_color=tema.BG_APP)
    fondos.aplicar(ventana_fiado, estilo="fiados")
    resp.fit_dialog(ventana_fiado, width_ratio=0.30, height_ratio=0.36, min_w=320, min_h=260, max_w=420, max_h=360)
    ventana_fiado.grab_set()

    card = tema.card(ventana_fiado)
    card.pack(fill="both", expand=True, padx=16, pady=16)

    title_lbl = tema.label(card, "Nuevo fiado", font=tema.FONT_HEADER)
    title_lbl.pack(anchor="w", padx=16, pady=(14, 10))

    tema.label(card, "Nombre", font=tema.FONT_SMALL, color=tema.TEXT_DIM).pack(anchor="w", padx=16)
    entrada_nombre = tema.entry(card)
    entrada_nombre.pack(fill="x", padx=16, pady=(2, 10))

    tema.label(card, "Monto pendiente", font=tema.FONT_SMALL, color=tema.TEXT_DIM).pack(anchor="w", padx=16)
    entrada_monto = tema.entry(card)
    entrada_monto.pack(fill="x", padx=16, pady=(2, 14))

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

        ejecutar(
            "INSERT INTO fiados (nombre_cliente, fecha, monto_pendiente) VALUES (?, ?, ?)",
            (nombre, fh.fecha_sql(), monto),
        )

        messagebox.showinfo("Guardado", f"Fiado guardado para {nombre}")

        if refrescar_func:
            refrescar_func()

        ventana_fiado.destroy()

    btn_guardar = tema.button(card, "Guardar", tema.ACCENT_GREEN, command=guardar_fiado, height=42)
    btn_guardar.pack(fill="x", padx=16, pady=(0, 16))

    anim.soft_entrance(
        ventana_fiado,
        title=title_lbl,
        panels=[card],
        buttons=[btn_guardar],
        accent=tema.ACCENT_GREEN,
    )
