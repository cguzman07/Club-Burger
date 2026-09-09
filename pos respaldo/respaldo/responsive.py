"""
Responsive layout — adapta ventanas y paneles al tamaño de pantalla.
Solo presentación; no toca lógica de negocio.
"""


def screen_size(win):
    """Devuelve (ancho, alto) de la pantalla donde vive la ventana."""
    try:
        win.update_idletasks()
    except Exception:
        pass
    return int(win.winfo_screenwidth()), int(win.winfo_screenheight())


def breakpoint(win):
    """
    Clasificación de pantalla:
      sm → laptops chicas / tablets (~<1280)
      md → escritorio estándar
      lg → monitores grandes / full HD+
    """
    w, h = screen_size(win)
    if w < 1280 or h < 720:
        return "sm"
    if w < 1680:
        return "md"
    return "lg"


def clamp(value, lo, hi):
    return max(lo, min(hi, int(value)))


def fit(
    win,
    width_ratio=0.88,
    height_ratio=0.88,
    min_w=720,
    min_h=520,
    max_w=None,
    max_h=None,
    center=True,
    resizable=True,
):
    """
    Dimensiona y centra una ventana según la pantalla actual.
    Usa ratios del monitor (no píxeles fijos).
    """
    sw, sh = screen_size(win)
    # deja margen para barras del sistema
    usable_h = max(480, sh - 48)

    w = clamp(sw * width_ratio, min_w, max_w if max_w is not None else sw)
    h = clamp(usable_h * height_ratio, min_h, max_h if max_h is not None else usable_h)

    # no exceder pantalla
    w = min(w, sw)
    h = min(h, usable_h)

    if center:
        x = max(0, (sw - w) // 2)
        y = max(0, (usable_h - h) // 2)
        win.geometry(f"{w}x{h}+{x}+{y}")
    else:
        win.geometry(f"{w}x{h}")

    try:
        win.minsize(min(min_w, w), min(min_h, h))
    except Exception:
        pass

    if resizable is not None:
        try:
            win.resizable(bool(resizable), bool(resizable))
        except Exception:
            pass

    return w, h


def fit_dialog(
    win,
    width_ratio=0.36,
    height_ratio=0.48,
    min_w=340,
    min_h=280,
    max_w=520,
    max_h=640,
):
    """Ventanas modales / formularios (más pequeñas, centradas)."""
    return fit(
        win,
        width_ratio=width_ratio,
        height_ratio=height_ratio,
        min_w=min_w,
        min_h=min_h,
        max_w=max_w,
        max_h=max_h,
        center=True,
        resizable=True,
    )


def fit_fullscreenish(win, margin=0.02):
    """Casi pantalla completa con pequeño margen (ideal caja / reportes)."""
    return fit(
        win,
        width_ratio=1 - margin * 2,
        height_ratio=1 - margin * 2,
        min_w=900,
        min_h=600,
        center=True,
        resizable=True,
    )


def metrics(win):
    """
    Métricas de layout por breakpoint.
    Úsalas para anchos de sidebar, carrito, tipografía relativa, etc.
    """
    bp = breakpoint(win)
    sw, sh = screen_size(win)

    if bp == "sm":
        return {
            "bp": bp,
            "screen": (sw, sh),
            "sidebar": 120,
            "cart": 360,
            "header_h": 56,
            "search_w": 160,
            "pad": 8,
            "product_cols": 2,
            "nav_w": 200,
            "font_scale": 0.92,
        }
    if bp == "md":
        return {
            "bp": bp,
            "screen": (sw, sh),
            "sidebar": 148,
            "cart": 420,
            "header_h": 64,
            "search_w": 260,
            "pad": 12,
            "product_cols": 3,
            "nav_w": 240,
            "font_scale": 1.0,
        }
    return {
        "bp": bp,
        "screen": (sw, sh),
        "sidebar": 168,
        "cart": 480,
        "header_h": 68,
        "search_w": 340,
        "pad": 14,
        "product_cols": 4,
        "nav_w": 260,
        "font_scale": 1.05,
    }


def product_columns_for_width(inner_width):
    """Columnas del grid de productos según ancho útil del panel central."""
    if inner_width < 520:
        return 2
    if inner_width < 820:
        return 3
    if inner_width < 1100:
        return 4
    return 5


def bind_resize(win, callback, delay_ms=120):
    """
    Llama callback(event) al redimensionar, con debounce.
    callback recibe el evento Configure de la ventana.
    """
    state = {"after": None, "last": (0, 0)}

    def on_configure(event):
        # solo importa resize de la ventana raíz, no de hijos
        if event.widget is not win:
            return
        w, h = event.width, event.height
        if (w, h) == state["last"]:
            return
        state["last"] = (w, h)
        if state["after"] is not None:
            try:
                win.after_cancel(state["after"])
            except Exception:
                pass

        def fire():
            state["after"] = None
            if win.winfo_exists():
                callback(event)

        state["after"] = win.after(delay_ms, fire)

    win.bind("<Configure>", on_configure)
    return on_configure
