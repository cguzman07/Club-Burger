import customtkinter as ctk
from ventana_inventario import ventana_inventario
from ventana_reportes import ventana_reportes
from apertura_caja import ventana_apertura_caja
from ventana_gestion_usuarios import ventana_gestion_usuarios
import tema_caja as tema
import animaciones as anim
import responsive as resp
from saludos import mostrar_bienvenida, mostrar_despedida
import fondos
import fechahora as fh


def cerrar_sesion(ventana, usuario=""):
    try:
        mostrar_despedida(usuario, parent=ventana)
    except Exception:
        pass
    try:
        ventana.destroy()
    except Exception:
        pass
    from ventana_login import iniciar_login

    iniciar_login()


def abrir_pantalla_principal(usuario, rol):
    tema.apply_theme()

    ventana = ctk.CTk()
    ventana.title("Club Burger POS")
    ventana.configure(fg_color="#1A120C")
    tema.apply_theme(ventana)

    resp.fit(
        ventana,
        width_ratio=0.92,
        height_ratio=0.90,
        min_w=800,
        min_h=520,
        resizable=True,
    )
    m = resp.metrics(ventana)
    nav_w = int(m["nav_w"])
    header_h = int(m["header_h"])

    fondos.aplicar(ventana, estilo="hub")

    brand = tema.brand_header(
        ventana,
        usuario=usuario,
        rol=rol,
        height=header_h,
        show_clock=True,
    )
    _ = brand["brand_title"]

    sidebar = ctk.CTkFrame(
        ventana,
        width=nav_w,
        height=400,
        fg_color=tema.BG_PANEL,
        corner_radius=0,
    )
    sidebar.place(x=0, y=header_h, relheight=1)
    sidebar.pack_propagate(False)

    ctk.CTkLabel(
        sidebar,
        text="MENÚ",
        font=tema.FONT_HEADER,
        text_color="#FFE8CC",
        fg_color="transparent",
    ).pack(anchor="w", padx=20, pady=(24, 14))

    nav_buttons = []

    def nav_btn(text, color, command):
        btn = tema.button(sidebar, text, color, command=command, height=50)
        btn.pack(fill="x", padx=14, pady=7)
        nav_buttons.append(btn)
        return btn

    nav_btn("🧾  Caja", tema.ACCENT_BLUE, lambda: ventana_apertura_caja(usuario, ventana))

    if rol == "admin":
        nav_btn("📦  Inventario", tema.ACCENT_GREEN_DARK, lambda: ventana_inventario(usuario, ventana))
        nav_btn("📊  Reportes", tema.ACCENT_ORANGE, lambda: ventana_reportes(usuario, ventana))
        nav_btn("👥  Usuarios", tema.ACCENT_PURPLE, lambda: ventana_gestion_usuarios(usuario, ventana))

    ctk.CTkFrame(sidebar, fg_color="transparent").pack(expand=True, fill="both")
    nav_btn("⛔  Cerrar sesión", tema.ACCENT_RED, lambda: cerrar_sesion(ventana, usuario))

    cards_meta = [
        ("Caja", "Cobro rápido, tickets e impresión", tema.ACCENT_BLUE, "🧾", lambda: ventana_apertura_caja(usuario, ventana)),
        ("Inventario", "Productos, precios y stock al día", tema.ACCENT_GREEN, "📦", lambda: ventana_inventario(usuario, ventana)),
        ("Reportes", "Ventas, gráficos y fiados", tema.ACCENT_ORANGE, "📊", lambda: ventana_reportes(usuario, ventana)),
        ("Usuarios", "Accesos y roles del equipo", tema.ACCENT_PURPLE, "👥", lambda: ventana_gestion_usuarios(usuario, ventana)),
    ]

    card_widgets = []

    def cols_for_width(w):
        return 1 if w < 900 else 2

    def _layout_letreros():
        pad = max(16, m["pad"] * 2)
        x = nav_w + pad
        y1 = header_h + pad
        wrap = max(280, ventana.winfo_width() - nav_w - pad * 2)
        fondos.letrero(
            ventana,
            "welcome",
            f"¡Hola, {str(usuario).title()}!",
            x,
            y1,
            fill="#FFFFFF",
            font=(tema.FONT_FAMILY, 28, "bold"),
            width=wrap,
        )
        fondos.letrero(
            ventana,
            "subtitle",
            f"Hoy es {fh.formatear_largo()}  ·  elige un módulo y dale con actitud",
            x,
            y1 + 44,
            fill="#FFD7A8",
            font=(tema.FONT_FAMILY, 14),
            width=wrap,
        )
        fondos.asegurar_al_fondo(ventana)

    def rebuild_cards(cols=2):
        for c in card_widgets:
            try:
                c.destroy()
            except Exception:
                pass
        card_widgets.clear()

        visible = [c for c in cards_meta if rol == "admin" or c[0] == "Caja"]
        pad = max(16, m["pad"] * 2)
        area_x = nav_w + pad
        area_y = header_h + pad + 86
        area_w = max(280, ventana.winfo_width() - nav_w - pad * 2)
        area_h = max(180, ventana.winfo_height() - area_y - pad)

        gap = 14
        card_w = max(220, (area_w - gap * (cols - 1)) // cols)
        rows = (len(visible) + cols - 1) // cols
        card_h = max(130, min(170, (area_h - gap * max(0, rows - 1)) // max(1, rows)))

        for i, (title_txt, desc, color, icon, cmd) in enumerate(visible):
            r, col = divmod(i, cols)
            x = area_x + col * (card_w + gap)
            y = area_y + r * (card_h + gap)

            c = ctk.CTkFrame(
                ventana,
                width=card_w,
                height=card_h,
                fg_color=tema.BG_CARD,
                corner_radius=18,
                border_width=1,
                border_color="#3A2A18",
                cursor="hand2",
            )
            c.place(x=x, y=y)
            c.pack_propagate(False)

            ctk.CTkLabel(
                c,
                text=f"{icon}  {title_txt}",
                font=tema.FONT_HEADER,
                text_color=color,
                fg_color="transparent",
            ).pack(anchor="w", padx=18, pady=(16, 4))
            ctk.CTkLabel(
                c,
                text=desc,
                font=tema.FONT_BODY,
                text_color="#E8DCCF",
                fg_color="transparent",
                wraplength=card_w - 36,
            ).pack(anchor="w", padx=18, pady=(0, 8))
            tema.button(c, "Abrir →", color, command=cmd, height=34, width=110).pack(
                anchor="w", padx=18, pady=(0, 12)
            )

            def on_enter(_e, frame=c, accent=color):
                frame.configure(border_width=2, border_color=accent)

            def on_leave(_e, frame=c):
                frame.configure(border_width=1, border_color="#3A2A18")

            c.bind("<Enter>", on_enter)
            c.bind("<Leave>", on_leave)
            card_widgets.append(c)

        fondos.asegurar_al_fondo(ventana)

    layout_state = {"cols": cols_for_width(ventana.winfo_width() or 980)}

    def on_resize(_event=None):
        _layout_letreros()
        cols = cols_for_width(max(400, ventana.winfo_width() - nav_w))
        layout_state["cols"] = cols
        rebuild_cards(cols)

    resp.bind_resize(ventana, on_resize)
    ventana.after(50, on_resize)

    def intro():
        fondos.asegurar_al_fondo(ventana)
        if nav_buttons:
            ventana.after(
                350,
                lambda: anim.pulse_button(
                    nav_buttons[0],
                    tema.ACCENT_BLUE,
                    anim.lighten(tema.ACCENT_BLUE, 0.3),
                    cycles=1,
                ),
            )
        ventana.after(480, lambda: mostrar_bienvenida(usuario, rol, parent=ventana))

    ventana.after(80, intro)
    ventana.mainloop()
