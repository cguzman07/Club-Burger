"""
Sistema de diseño Club Burger POS — modo oscuro profesional.
Solo apariencia. Sin lógica de negocio.
"""
from tkinter import ttk
import customtkinter as ctk

# ---------- Fondos ----------
BG_APP = "#121212"
BG_PANEL = "#1A1A1A"
BG_CARD = "#222222"
BG_INPUT = "#2A2A2A"
BG_HOVER = "#2F2F2F"
BG_TREE = "#1E1E1E"
BG_TREE_SEL = "#FF8C00"

# ---------- Texto ----------
TEXT = "#FFFFFF"
TEXT_DIM = "#A0A0A0"
TEXT_MUTED = "#6B6B6B"

# ---------- Acentos ----------
ACCENT_ORANGE = "#FF8C00"
ACCENT_GREEN = "#00C853"
ACCENT_GREEN_DARK = "#1B5E20"
ACCENT_BLUE = "#1565C0"
ACCENT_PURPLE = "#6A1B9A"
ACCENT_YELLOW = "#F9A825"
ACCENT_CYAN = "#29B6F6"
ACCENT_MINT = "#26A69A"
ACCENT_RED = "#E53935"
ACCENT_GRAY = "#616161"
ACCENT_TEAL = "#00897B"

CATEGORY_COLORS = [
    ACCENT_ORANGE,
    ACCENT_YELLOW,
    ACCENT_CYAN,
    ACCENT_MINT,
    ACCENT_PURPLE,
    "#EF5350",
    "#7E57C2",
    "#42A5F5",
]

# ---------- Tipografía ----------
FONT_FAMILY = "Segoe UI"
FONT_TITLE = (FONT_FAMILY, 22, "bold")
FONT_HEADER = (FONT_FAMILY, 14, "bold")
FONT_BODY = (FONT_FAMILY, 13)
FONT_BODY_BOLD = (FONT_FAMILY, 13, "bold")
FONT_SMALL = (FONT_FAMILY, 11)
FONT_TOTAL = (FONT_FAMILY, 20, "bold")
FONT_BTN = (FONT_FAMILY, 13, "bold")
FONT_BTN_LG = (FONT_FAMILY, 15, "bold")
FONT_HERO = (FONT_FAMILY, 28, "bold")

# ---------- Radios ----------
RADIUS = 16
RADIUS_SM = 12
RADIUS_BTN = 18


def apply_theme(win=None):
    """Aplica tema oscuro global CustomTkinter (+ scaling suave por pantalla)."""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    if win is not None:
        try:
            import responsive as resp

            bp = resp.breakpoint(win)
            if bp == "sm":
                ctk.set_widget_scaling(0.95)
                ctk.set_window_scaling(0.95)
            elif bp == "lg":
                ctk.set_widget_scaling(1.08)
                ctk.set_window_scaling(1.05)
            else:
                ctk.set_widget_scaling(1.0)
                ctk.set_window_scaling(1.0)
        except Exception:
            pass
        try:
            from iconos import apply_window_icon

            apply_window_icon(win)
        except Exception:
            pass


def _lighten(hex_color, amount=0.2):
    hx = hex_color.lstrip("#")
    r, g, b = int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)
    r = min(255, int(r + (255 - r) * amount))
    g = min(255, int(g + (255 - g) * amount))
    b = min(255, int(b + (255 - b) * amount))
    return f"#{r:02x}{g:02x}{b:02x}"


def button(parent, text, color, command=None, height=44, font=None, **kwargs):
    """Botón alegre: hover más luminoso (no gris), bordes muy redondos."""
    hover = kwargs.pop("hover_color", None) or _lighten(color, 0.22)
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        fg_color=color,
        hover_color=hover,
        text_color=TEXT,
        corner_radius=RADIUS_BTN,
        height=height,
        border_width=0,
        font=font or FONT_BTN,
        **kwargs,
    )


def label(parent, text, font=None, color=None, **kwargs):
    kwargs.setdefault("fg_color", "transparent")
    return ctk.CTkLabel(
        parent,
        text=text,
        font=font or FONT_BODY,
        text_color=color or "#FFE8CC",
        **kwargs,
    )


def entry(parent, **kwargs):
    defaults = dict(
        height=36,
        corner_radius=RADIUS_SM,
        fg_color=BG_INPUT,
        border_width=0,
        font=FONT_BODY,
        text_color=TEXT,
    )
    defaults.update(kwargs)
    return ctk.CTkEntry(parent, **defaults)


def panel(parent, **kwargs):
    defaults = dict(fg_color=BG_PANEL, corner_radius=RADIUS)
    defaults.update(kwargs)
    return ctk.CTkFrame(parent, **defaults)


def card(parent, **kwargs):
    defaults = dict(fg_color=BG_CARD, corner_radius=RADIUS)
    defaults.update(kwargs)
    return ctk.CTkFrame(parent, **defaults)


def style_treeview(root_or_style=None):
    """Estilo oscuro profesional para ttk.Treeview (CTK no tiene tabla nativa)."""
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure(
        "Dark.Treeview",
        background=BG_TREE,
        foreground=TEXT,
        fieldbackground=BG_TREE,
        borderwidth=0,
        rowheight=32,
        font=(FONT_FAMILY, 11),
    )
    style.configure(
        "Dark.Treeview.Heading",
        background=BG_CARD,
        foreground=TEXT,
        relief="flat",
        font=(FONT_FAMILY, 11, "bold"),
        borderwidth=0,
    )
    style.map(
        "Dark.Treeview",
        background=[("selected", BG_TREE_SEL)],
        foreground=[("selected", "#111111")],
    )
    style.map("Dark.Treeview.Heading", background=[("active", BG_HOVER)])
    return style


def dark_matplotlib(fig, axs):
    """Aplica fondo oscuro a figuras matplotlib embebidas."""
    fig.patch.set_facecolor(BG_PANEL)
    axes_list = axs if hasattr(axs, "__len__") else [axs]
    for ax in axes_list:
        ax.set_facecolor(BG_CARD)
        ax.tick_params(colors=TEXT_DIM)
        ax.xaxis.label.set_color(TEXT_DIM)
        ax.yaxis.label.set_color(TEXT_DIM)
        ax.title.set_color(TEXT)
        for spine in ax.spines.values():
            spine.set_color(TEXT_MUTED)
        ax.grid(True, color="#333333", linestyle="--", alpha=0.5)


def brand_header(parent, usuario=None, rol=None, height=68, show_clock=True, extra_left=None):
    """
    Barra superior con marca Club Burger + chip de usuario + reloj local en vivo.
    Devuelve dict con referencias: header, brand_title, user_name, clock_lbl
    """
    import fechahora as fh

    header = ctk.CTkFrame(parent, fg_color=BG_PANEL, corner_radius=0, height=height)
    header.pack(fill="x", side="top")
    header.pack_propagate(False)

    # Acento vertical naranja (marca)
    accent = ctk.CTkFrame(header, fg_color=ACCENT_ORANGE, width=5, corner_radius=0)
    accent.pack(side="left", fill="y")

    brand_wrap = ctk.CTkFrame(header, fg_color="transparent")
    brand_wrap.pack(side="left", padx=(14, 8), pady=8)

    logo = ctk.CTkFrame(brand_wrap, fg_color=ACCENT_ORANGE, width=42, height=42, corner_radius=21)
    logo.pack(side="left", padx=(0, 10))
    logo.pack_propagate(False)
    _logo_ok = False
    try:
        import os
        from paths import logo_ui_path
        from PIL import Image

        _lp = logo_ui_path()
        if os.path.exists(_lp):
            _pil = Image.open(_lp).convert("RGBA").resize((40, 40))
            _ctk = ctk.CTkImage(light_image=_pil, dark_image=_pil, size=(40, 40))
            ctk.CTkLabel(logo, text="", image=_ctk).place(relx=0.5, rely=0.5, anchor="center")
            if not hasattr(header, "_cb_logo_refs"):
                header._cb_logo_refs = []
            header._cb_logo_refs.append(_ctk)
            _logo_ok = True
    except Exception:
        _logo_ok = False
    if not _logo_ok:
        ctk.CTkLabel(
            logo,
            text="CB",
            font=(FONT_FAMILY, 14, "bold"),
            text_color="#111111",
        ).place(relx=0.5, rely=0.5, anchor="center")

    brand_text = ctk.CTkFrame(brand_wrap, fg_color="transparent")
    brand_text.pack(side="left")
    brand_title = ctk.CTkLabel(
        brand_text,
        text="Club Burger",
        font=(FONT_FAMILY, 20, "bold"),
        text_color="#FFFFFF",
        fg_color="transparent",
    )
    brand_title.pack(anchor="w")
    ctk.CTkLabel(
        brand_text,
        text="POS  ·  punto de venta",
        font=FONT_SMALL,
        text_color="#FFD7A8",
        fg_color="transparent",
    ).pack(anchor="w")

    if callable(extra_left):
        extra_left(header)

    # Derecha: reloj + usuario
    right = ctk.CTkFrame(header, fg_color="transparent")
    right.pack(side="right", padx=14, pady=8)

    clock_lbl = None
    if show_clock:
        clock_box = ctk.CTkFrame(right, fg_color=BG_CARD, corner_radius=RADIUS_SM)
        clock_box.pack(side="right", padx=(10, 0))
        clock_lbl = ctk.CTkLabel(
            clock_box,
            text=fh.formatear_header(),
            font=(FONT_FAMILY, 12, "bold"),
            text_color=ACCENT_ORANGE,
            fg_color="transparent",
        )
        clock_lbl.pack(padx=12, pady=8)

        def _tick():
            if clock_lbl.winfo_exists():
                clock_lbl.configure(text=fh.formatear_header())
                clock_lbl.after(1000, _tick)

        clock_lbl.after(1000, _tick)

    user_name = None
    if usuario:
        chip = ctk.CTkFrame(
            right,
            fg_color=BG_CARD,
            corner_radius=RADIUS,
            border_width=1,
            border_color="#333333",
        )
        chip.pack(side="right")

        initial = (usuario[:1] or "?").upper()
        avatar = ctk.CTkFrame(chip, fg_color=ACCENT_ORANGE, width=36, height=36, corner_radius=18)
        avatar.pack(side="left", padx=(8, 8), pady=6)
        avatar.pack_propagate(False)
        ctk.CTkLabel(
            avatar,
            text=initial,
            font=(FONT_FAMILY, 14, "bold"),
            text_color="#111111",
        ).place(relx=0.5, rely=0.5, anchor="center")

        info = ctk.CTkFrame(chip, fg_color="transparent")
        info.pack(side="left", padx=(0, 12), pady=6)
        user_name = ctk.CTkLabel(
            info,
            text=str(usuario).title(),
            font=(FONT_FAMILY, 14, "bold"),
            text_color="#FFFFFF",
            fg_color="transparent",
        )
        user_name.pack(anchor="w")
        rol_txt = (rol or "cajero").capitalize()
        ctk.CTkLabel(
            info,
            text=f"●  {rol_txt} en turno",
            font=FONT_SMALL,
            text_color=ACCENT_GREEN,
            fg_color="transparent",
        ).pack(anchor="w")

    return {
        "header": header,
        "brand_title": brand_title,
        "user_name": user_name,
        "clock_lbl": clock_lbl,
    }
