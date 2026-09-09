"""
Utilidades de animación UI (solo apariencia).
Usan widget.after() — no tocan lógica de negocio.
"""


def _clamp(v, lo=0, hi=255):
    return max(lo, min(hi, int(v)))


def mix_hex(c1, c2, t):
    """Interpola dos colores hex. t=0 → c1, t=1 → c2."""
    c1 = c1.lstrip("#")
    c2 = c2.lstrip("#")
    r1, g1, b1 = int(c1[0:2], 16), int(c1[2:4], 16), int(c1[4:6], 16)
    r2, g2, b2 = int(c2[0:2], 16), int(c2[2:4], 16), int(c2[4:6], 16)
    r = _clamp(r1 + (r2 - r1) * t)
    g = _clamp(g1 + (g2 - g1) * t)
    b = _clamp(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def lighten(hex_color, amount=0.22):
    return mix_hex(hex_color, "#FFFFFF", amount)


def darken(hex_color, amount=0.18):
    return mix_hex(hex_color, "#000000", amount)


def fade_fg(widget, start, end, steps=12, delay=18, attr="text_color"):
    """Transición suave de color en labels/botones CTk."""

    def step(i=0):
        if not widget.winfo_exists():
            return
        t = i / steps
        color = mix_hex(start, end, t)
        try:
            widget.configure(**{attr: color})
        except Exception:
            return
        if i < steps:
            widget.after(delay, lambda: step(i + 1))

    step()


def slide_place(widget, x, y_from, y_to, steps=16, delay=14, on_done=None):
    """Desplaza un widget colocado con .place() de y_from → y_to."""

    def step(i=0):
        if not widget.winfo_exists():
            return
        t = i / steps
        eased = 1 - (1 - t) ** 3
        y = y_from + (y_to - y_from) * eased
        widget.place(relx=x, y=y, anchor="n")
        if i < steps:
            widget.after(delay, lambda: step(i + 1))
        elif on_done:
            on_done()

    step()


def shake(widget, amplitude=8, shakes=6, delay=22):
    """Sacudida horizontal (ideal para error de login)."""
    try:
        info = widget.place_info()
        base_x = float(info.get("relx", 0.5))
    except Exception:
        return

    sequence = []
    for i in range(shakes):
        direction = 1 if i % 2 == 0 else -1
        offset = (amplitude * direction) * (1 - i / shakes)
        sequence.append(offset)
    sequence.append(0)

    def step(idx=0):
        if not widget.winfo_exists() or idx >= len(sequence):
            return
        try:
            widget.place_configure(relx=base_x, x=sequence[idx])
        except Exception:
            return
        widget.after(delay, lambda: step(idx + 1))

    step()


def pulse_button(button, color_a, color_b, steps=10, delay=40, cycles=2):
    """Pulso suave del color de un botón (atención amigable)."""
    state = {"cycle": 0, "dir": 1, "i": 0}

    def step():
        if not button.winfo_exists():
            return
        t = state["i"] / steps
        if state["dir"] < 0:
            t = 1 - t
        color = mix_hex(color_a, color_b, t)
        try:
            button.configure(fg_color=color, hover_color=lighten(color, 0.12))
        except Exception:
            return
        state["i"] += 1
        if state["i"] > steps:
            state["i"] = 0
            state["dir"] *= -1
            state["cycle"] += 0.5
        if state["cycle"] < cycles:
            button.after(delay, step)

    step()


def pop_border(widget, accent="#FF8C00", hold_ms=150, width=2):
    """Destello rápido de borde (efecto 'aparición')."""
    if not widget or not widget.winfo_exists():
        return
    try:
        prev_w = int(widget.cget("border_width") or 0)
    except Exception:
        prev_w = 0
    try:
        widget.configure(border_width=width, border_color=accent)
    except Exception:
        return

    def restore():
        if widget.winfo_exists():
            try:
                widget.configure(border_width=prev_w)
            except Exception:
                pass

    widget.after(hold_ms, restore)


def cascade_pop(widgets, accent="#FF8C00", delay_between=55, start_delay=90, hold_ms=140):
    """Cascada de pop_border sobre una lista de widgets."""
    items = [w for w in widgets if w is not None]

    def reveal(idx=0):
        if idx >= len(items):
            return
        w = items[idx]
        if w.winfo_exists():
            pop_border(w, accent=accent, hold_ms=hold_ms)
        if idx + 1 < len(items):
            items[0].after(delay_between, lambda: reveal(idx + 1))

    if items:
        items[0].after(start_delay, lambda: reveal(0))


def float_blob(canvas, item_id, amp=10, period_ms=2800):
    """Oscilación vertical suave de un oval en Canvas."""
    state = {"t": 0, "base": None}

    def tick():
        if not canvas.winfo_exists():
            return
        try:
            coords = canvas.coords(item_id)
            if len(coords) < 4:
                return
            if state["base"] is None:
                state["base"] = coords[:]
            import math

            state["t"] += 1
            dy = math.sin(state["t"] / (period_ms / 40)) * amp
            b = state["base"]
            canvas.coords(item_id, b[0], b[1] + dy, b[2], b[3] + dy)
        except Exception:
            return
        canvas.after(40, tick)

    canvas.after(40, tick)


def soft_entrance(
    root,
    title=None,
    panels=None,
    buttons=None,
    accent="#FF8C00",
    title_from="#121212",
    title_to="#FFFFFF",
):
    """
    Entrada estándar para paneles:
    1) título con fade
    2) paneles con pop en cascada
    3) botones con pop + pulso suave del primero
    """
    if not root or not root.winfo_exists():
        return

    if title is not None and title.winfo_exists():
        try:
            title.configure(text_color=title_from)
        except Exception:
            pass
        fade_fg(title, title_from, title_to, steps=12, delay=16)

    panel_list = list(panels or [])
    btn_list = list(buttons or [])

    if panel_list:
        cascade_pop(panel_list, accent=accent, delay_between=70, start_delay=120, hold_ms=160)

    if btn_list:
        cascade_pop(btn_list, accent=lighten(accent, 0.25), delay_between=45, start_delay=220, hold_ms=120)

        first = btn_list[0]
        try:
            base = first.cget("fg_color")
            if isinstance(base, (tuple, list)):
                base = base[-1]
        except Exception:
            base = accent

        def _pulse():
            if first.winfo_exists():
                pulse_button(first, base, lighten(str(base), 0.35), cycles=1)

        root.after(420, _pulse)
