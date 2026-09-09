import sqlite3
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

from ventana_principal import abrir_pantalla_principal
from database import inicializar_db
import tema_caja as tema
import animaciones as anim
import responsive as resp
import fechahora as fh
import fondos


def _saludo_hora():
    h = fh.ahora().hour
    if h < 12:
        return "Buenos días"
    if h < 19:
        return "Buenas tardes"
    return "Buenas noches"


def iniciar_login():
    inicializar_db()
    tema.apply_theme()

    ventana_login = ctk.CTk()
    ventana_login.title("Club Burger POS — Inicio de sesión")
    ventana_login.configure(fg_color="#1A120C")
    tema.apply_theme(ventana_login)

    win_w, win_h = resp.fit(
        ventana_login,
        width_ratio=0.42,
        height_ratio=0.86,
        min_w=420,
        min_h=560,
        max_w=560,
        max_h=780,
        resizable=True,
    )
    m = resp.metrics(ventana_login)

    fondos.aplicar(ventana_login, estilo="login")

    # Logo (único chip con fondo; el resto son letras sobre la foto)
    logo_wrap = ctk.CTkFrame(
        ventana_login, fg_color=tema.BG_CARD, width=64, height=64, corner_radius=20
    )
    logo_wrap.place(relx=0.5, rely=0.02, anchor="n")
    logo_wrap.pack_propagate(False)
    try:
        from paths import logo_ui_path
        from PIL import Image
        import os

        _lp = logo_ui_path()
        if os.path.exists(_lp):
            _pil = Image.open(_lp).convert("RGBA").resize((56, 56))
            _cimg = ctk.CTkImage(light_image=_pil, dark_image=_pil, size=(56, 56))
            ctk.CTkLabel(logo_wrap, text="", image=_cimg).place(relx=0.5, rely=0.5, anchor="center")
            ventana_login._cb_logo_refs = [_cimg]
        else:
            raise FileNotFoundError(_lp)
    except Exception:
        logo_wrap.configure(fg_color=tema.ACCENT_ORANGE)
        ctk.CTkLabel(
            logo_wrap,
            text="CB",
            font=(tema.FONT_FAMILY, 16, "bold"),
            text_color="#111111",
        ).place(relx=0.5, rely=0.5, anchor="center")

    # Solo letras sobre la foto (sin cajas negras de CTkLabel)
    def _layout_login_text(_e=None):
        w = max(ventana_login.winfo_width(), 420)
        h = max(ventana_login.winfo_height(), 560)
        fondos.letrero(
            ventana_login,
            "brand",
            "Club Burger",
            w // 2,
            int(h * 0.115),
            fill="#FFFFFF",
            font=(tema.FONT_FAMILY, 30 if m["bp"] == "sm" else 34, "bold"),
            anchor="n",
        )
        fondos.letrero(
            ventana_login,
            "tagline",
            f"{_saludo_hora()}  ·  {fh.formatear_header()}",
            w // 2,
            int(h * 0.175),
            fill="#FFB347",
            font=(tema.FONT_FAMILY, 13),
            anchor="n",
        )
        fondos.letrero(
            ventana_login,
            "footer",
            "POS  •  Versión 1.1  •  Hecho para tu mejor turno",
            w // 2,
            int(h * 0.97),
            fill="#FFE8CC",
            font=(tema.FONT_FAMILY, 11),
            anchor="s",
        )

    def _tick_login():
        try:
            if not ventana_login.winfo_exists():
                return
        except Exception:
            return
        w = max(ventana_login.winfo_width(), 420)
        h = max(ventana_login.winfo_height(), 560)
        fondos.letrero(
            ventana_login,
            "tagline",
            f"{_saludo_hora()}  ·  {fh.formatear_header()}",
            w // 2,
            int(h * 0.175),
            fill="#FFB347",
            font=(tema.FONT_FAMILY, 13),
            anchor="n",
        )
        ventana_login.after(1000, _tick_login)

    ventana_login.after(60, _layout_login_text)
    ventana_login.after(1200, _tick_login)

    card_w = min(400, max(320, int(win_w * 0.78)))
    card_h = min(400, max(340, int(win_h * 0.58)))

    # Formulario: sí necesita panel para leer los campos
    card = ctk.CTkFrame(
        ventana_login,
        width=card_w,
        height=card_h,
        fg_color=tema.BG_CARD,
        corner_radius=22,
        border_width=1,
        border_color="#3A2A18",
    )
    card.place(relx=0.5, rely=1.15, anchor="n")
    card.pack_propagate(False)

    inner = ctk.CTkFrame(card, fg_color="transparent")
    inner.pack(fill="both", expand=True, padx=max(18, int(card_w * 0.07)), pady=18)

    ctk.CTkLabel(
        inner, text="Iniciar sesión", font=tema.FONT_HEADER, text_color=tema.TEXT, fg_color="transparent"
    ).pack(anchor="w", pady=(4, 4))
    ctk.CTkLabel(
        inner,
        text="Tu turno empieza aquí. ¡Vamos con energía!",
        font=tema.FONT_SMALL,
        text_color=tema.TEXT_DIM,
        fg_color="transparent",
    ).pack(anchor="w", pady=(0, 12))

    ctk.CTkLabel(inner, text="Usuario", font=tema.FONT_SMALL, text_color=tema.TEXT_DIM, fg_color="transparent").pack(
        anchor="w"
    )
    entry_usuario = tema.entry(inner, height=42, corner_radius=14)
    entry_usuario.pack(fill="x", pady=(4, 10))
    entry_usuario.focus()

    ctk.CTkLabel(
        inner, text="Contraseña", font=tema.FONT_SMALL, text_color=tema.TEXT_DIM, fg_color="transparent"
    ).pack(anchor="w")

    pwd_row = ctk.CTkFrame(inner, fg_color="transparent")
    pwd_row.pack(fill="x", pady=(4, 6))

    entry_contrasena = tema.entry(pwd_row, show="*", height=42, corner_radius=14)
    entry_contrasena.pack(side="left", fill="x", expand=True)

    def toggle_password():
        if entry_contrasena.cget("show") == "":
            entry_contrasena.configure(show="*")
            btn_toggle.configure(text="Ver")
        else:
            entry_contrasena.configure(show="")
            btn_toggle.configure(text="Ocultar")

    btn_toggle = ctk.CTkButton(
        pwd_row,
        text="Ver",
        width=78,
        height=42,
        fg_color=tema.BG_INPUT,
        hover_color=anim.lighten(tema.BG_INPUT, 0.15),
        corner_radius=14,
        font=tema.FONT_SMALL,
        command=toggle_password,
    )
    btn_toggle.pack(side="left", padx=(10, 0))

    error_var = tk.StringVar()
    ctk.CTkLabel(
        inner,
        textvariable=error_var,
        font=tema.FONT_SMALL,
        text_color=tema.ACCENT_RED,
        height=18,
        fg_color="transparent",
    ).pack(fill="x", pady=(2, 4))

    # Transición segura: salir del mainloop del login y luego abrir el hub
    pending = {"usuario": None, "rol": None}

    def verificar_credenciales(event=None):
        usuario = entry_usuario.get().strip()
        contrasena = entry_contrasena.get()

        try:
            conn = sqlite3.connect("datos_pos.db")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT rol FROM usuarios WHERE usuario=? AND contrasena=?",
                (usuario, contrasena),
            )
            resultado = cursor.fetchone()
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo validar el usuario:\n{e}")
            return

        if resultado:
            pending["usuario"] = usuario
            pending["rol"] = resultado[0]
            btn_entrar.configure(text="¡Listo!  →", fg_color=tema.ACCENT_GREEN)
            ventana_login.after(220, ventana_login.quit)
        else:
            error_var.set("Ups — usuario o contraseña incorrectos")
            anim.shake(card, amplitude=10, shakes=7)
            anim.pulse_button(btn_entrar, tema.ACCENT_ORANGE, "#FF5252", cycles=1)

    btn_entrar = ctk.CTkButton(
        inner,
        text="→  Entrar al turno",
        command=verificar_credenciales,
        height=48,
        corner_radius=20,
        fg_color=tema.ACCENT_ORANGE,
        hover_color=anim.lighten(tema.ACCENT_ORANGE, 0.25),
        font=(tema.FONT_FAMILY, 15, "bold"),
        text_color="#111111",
    )
    btn_entrar.pack(fill="x", pady=(6, 4))

    tips = [
        "Consejo: un saludo amable vende tanto como el producto.",
        "Tip: confirma el cambio en voz alta — el cliente lo agradece.",
        "Ánimo: cada ticket es una experiencia Club Burger.",
        "Hoy es buen día para un servicio impecable.",
    ]
    tip_lbl = ctk.CTkLabel(
        inner,
        text=tips[fh.ahora().second % len(tips)],
        font=tema.FONT_SMALL,
        text_color=tema.TEXT_MUTED,
        wraplength=max(240, card_w - 60),
        justify="left",
        fg_color="transparent",
    )
    tip_lbl.pack(anchor="w", pady=(10, 0))

    tip_idx = {"i": fh.ahora().second % len(tips)}

    def rotar_tip():
        if not tip_lbl.winfo_exists():
            return
        tip_idx["i"] = (tip_idx["i"] + 1) % len(tips)
        tip_lbl.configure(text=tips[tip_idx["i"]])
        tip_lbl.after(4500, rotar_tip)

    tip_lbl.after(4500, rotar_tip)

    entry_usuario.bind("<Return>", verificar_credenciales)
    entry_contrasena.bind("<Return>", verificar_credenciales)

    def on_resize(_event=None):
        tip_lbl.configure(wraplength=max(220, ventana_login.winfo_width() - 120))
        _layout_login_text()

    resp.bind_resize(ventana_login, on_resize)

    def start_motion():
        fondos.asegurar_al_fondo(ventana_login)

        def slide_card(i=0, steps=18):
            if not card.winfo_exists():
                return
            t = i / steps
            eased = 1 - (1 - t) ** 3
            rely = 1.15 + (0.24 - 1.15) * eased
            card.place(relx=0.5, rely=rely, anchor="n")
            if i < steps:
                card.after(14, lambda: slide_card(i + 1, steps))
            else:
                anim.pulse_button(
                    btn_entrar,
                    tema.ACCENT_ORANGE,
                    anim.lighten(tema.ACCENT_ORANGE, 0.35),
                    cycles=1.5,
                )
                fondos.asegurar_al_fondo(ventana_login)

        slide_card()

    ventana_login.after(80, start_motion)
    ventana_login.after(120, lambda: fondos.asegurar_al_fondo(ventana_login))
    ventana_login.mainloop()

    # Tras quit(): cerrar login y abrir hub (sin anidar mainloops a la fuerza)
    u = pending["usuario"]
    r = pending["rol"]
    try:
        ventana_login.destroy()
    except Exception:
        pass

    if u and r:
        try:
            abrir_pantalla_principal(u, r)
        except Exception as e:
            messagebox.showerror(
                "Error al abrir el menú",
                f"El inicio de sesión fue correcto, pero falló la pantalla principal:\n{e}",
            )
            iniciar_login()
