import sqlite3
from datetime import datetime
from tkinter import messagebox, StringVar
import customtkinter as ctk

from ventana_caja import ventana_caja
from database import obtener_caja_abierta, inicializar_db
import tema_caja as tema
import responsive as resp
import animaciones as anim
import fechahora as fh
from iconos import apply_window_icon
import fondos


def ventana_apertura_caja(usuario, ventana_anterior):
    inicializar_db()

    # Sesión abierta = cualquier caja sin cerrar (aunque sea de ayer / cruzó medianoche)
    fila_caja = obtener_caja_abierta(usuario)

    if fila_caja:
        ventana_caja(usuario, ventana_anterior)
        return

    ventana_anterior.withdraw()
    tema.apply_theme()

    ventana = ctk.CTkToplevel()
    ventana.title("Apertura de Caja")
    ventana.configure(fg_color="#1A120C")
    apply_window_icon(ventana)
    fondos.aplicar(ventana, estilo="apertura")
    resp.fit(
        ventana,
        width_ratio=0.42,
        height_ratio=0.92,
        min_w=420,
        min_h=560,
        max_w=640,
        max_h=900,
        resizable=True,
    )

    ahora = fh.ahora()
    scroll = ctk.CTkScrollableFrame(ventana, fg_color="#1A120C", corner_radius=0)
    scroll.pack(fill="both", expand=True, padx=18, pady=18)
    ventana.after(100, lambda: fondos.asegurar_al_fondo(ventana))
    ventana.after(150, lambda: fondos.labels_transparantes(ventana))

    card = tema.card(scroll)
    card.pack(fill="x")

    title_lbl = tema.label(card, "Apertura de Caja", font=tema.FONT_TITLE)
    title_lbl.pack(pady=(22, 4))
    tema.label(
        card,
        f"Usuario: {usuario}  ·  {fh.formatear_header(ahora)}",
        font=tema.FONT_SMALL,
        color=tema.TEXT_DIM,
    ).pack(pady=(0, 8))
    tema.label(
        card,
        "La sesión permanece abierta aunque pase medianoche, hasta que cierres caja.",
        font=tema.FONT_SMALL,
        color=tema.ACCENT_ORANGE,
    ).pack(padx=24, pady=(0, 16))

    denominaciones = [
        ("Billetes de $100.000", 100000),
        ("Billetes de $50.000", 50000),
        ("Billetes de $20.000", 20000),
        ("Billetes de $10.000", 10000),
        ("Billetes de $5.000", 5000),
        ("Billetes de $2.000", 2000),
        ("Monedas de $1.000", 1000),
        ("Monedas de $500", 500),
        ("Monedas de $200", 200),
        ("Monedas de $100", 100),
        ("Monedas de $50", 50),
    ]

    entradas = {}
    total_var = StringVar(value="Total: $0")

    def calcular_total():
        total = 0
        for valor, entrada in entradas.items():
            try:
                cantidad = int(entrada.get())
            except ValueError:
                cantidad = 0
            total += valor * cantidad
        total_var.set(f"Total: ${total:,}".replace(",", "."))
        return total

    for texto, valor in denominaciones:
        fila = ctk.CTkFrame(card, fg_color="transparent")
        fila.pack(fill="x", padx=24, pady=4)
        tema.label(fila, texto, font=tema.FONT_BODY, color=tema.TEXT_DIM).pack(side="left")
        entrada = tema.entry(fila, width=90)
        entrada.pack(side="right")
        entrada.insert(0, "0")
        entradas[valor] = entrada
        entrada.bind("<KeyRelease>", lambda e: calcular_total())

    ctk.CTkLabel(
        card,
        textvariable=total_var,
        font=tema.FONT_TOTAL,
        text_color=tema.ACCENT_GREEN,
    ).pack(pady=18)

    def guardar_apertura(usuario_inner, entradas_inner, ventana_actual, ventana_prev):
        total = calcular_total()
        if total == 0:
            messagebox.showwarning("Advertencia", "El total de caja inicial no puede ser 0.")
            return

        detalle_capital = "; ".join(
            f"{texto}: {entradas_inner[valor].get()}" for texto, valor in denominaciones
        )

        fecha_apertura = fh.fecha_sql()
        hora_apertura = fh.hora_sql()

        with sqlite3.connect("datos_pos.db") as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO caja (usuario, fecha, hora_apertura, capital_inicial, detalle_capital)
                VALUES (?, ?, ?, ?, ?)
            """,
                (usuario_inner, fecha_apertura, hora_apertura, total, detalle_capital),
            )

        messagebox.showinfo(
            "Éxito",
            f"Apertura registrada ({fecha_apertura} {hora_apertura})\n"
            f"Total inicial: ${total:,}".replace(",", "."),
        )
        ventana_actual.destroy()
        ventana_caja(usuario_inner, ventana_prev)

    btn_guardar = tema.button(
        card,
        "Guardar y Continuar",
        tema.ACCENT_GREEN,
        command=lambda: guardar_apertura(usuario, entradas, ventana, ventana_anterior),
        height=48,
        font=tema.FONT_BTN_LG,
    )
    btn_guardar.pack(fill="x", padx=24, pady=(4, 8))

    btn_volver = tema.button(
        card,
        "← Volver",
        tema.ACCENT_GRAY,
        command=lambda: (ventana.destroy(), ventana_anterior.deiconify()),
        height=40,
    )
    btn_volver.pack(fill="x", padx=24, pady=(0, 22))

    anim.soft_entrance(
        ventana,
        title=title_lbl,
        panels=[card],
        buttons=[btn_guardar, btn_volver],
        accent=tema.ACCENT_GREEN,
    )
