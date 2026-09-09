"""
Fondos fotográficos + letreros sin caja negra.
CustomTkinter: fg_color='transparent' NO deja ver la foto (pinta el color del padre).
Solución: canvas con la foto + create_text (solo letras, con sombra legible).
"""
from __future__ import annotations

import os
import tkinter as tk
from typing import Optional

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageTk

from paths import asset_path

_ESTILOS = {
    "login": ("fondo_hotdogs.png", 0.28, 1.12),
    "hub": ("fondo_burgers.png", 0.32, 1.08),
    "caja": ("fondo_burgers.png", 0.42, 1.05),
    "apertura": ("fondo_hotdogs.png", 0.30, 1.10),
    "admin": ("fondo_burgers.png", 0.34, 1.06),
    "reportes": ("fondo_burgers.png", 0.36, 1.05),
    "fiados": ("fondo_hotdogs.png", 0.32, 1.08),
    "saludo": ("fondo_burgers.png", 0.38, 1.06),
}


def _abrir_fuente(estilo: str) -> Optional[Image.Image]:
    nombre, _, _ = _ESTILOS.get(estilo, _ESTILOS["hub"])
    path = asset_path(nombre)
    if not os.path.exists(path):
        for alt in ("fondo_burgers.png", "fondo_hotdogs.png"):
            p = asset_path(alt)
            if os.path.exists(p):
                path = p
                break
        else:
            return None
    try:
        return Image.open(path).convert("RGB")
    except Exception:
        return None


def _cover(img: Image.Image, w: int, h: int) -> Image.Image:
    w, h = max(2, int(w)), max(2, int(h))
    iw, ih = img.size
    scale = max(w / max(iw, 1), h / max(ih, 1))
    nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
    resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
    left = (nw - w) // 2
    top = (nh - h) // 2
    return resized.crop((left, top, left + w, top + h))


def preparar(estilo: str, w: int, h: int) -> Optional[Image.Image]:
    base = _abrir_fuente(estilo)
    if base is None:
        return None
    _, oscuridad, calidez = _ESTILOS.get(estilo, _ESTILOS["hub"])
    frame = _cover(base, w, h)
    frame = ImageEnhance.Color(frame).enhance(calidez)
    frame = ImageEnhance.Contrast(frame).enhance(1.06)
    frame = ImageEnhance.Brightness(frame).enhance(1.02)
    veil = Image.new("RGB", frame.size, (28, 18, 10))
    frame = Image.blend(frame, veil, max(0.18, min(0.48, oscuridad)))
    vignette = Image.new("L", frame.size, 0)
    draw = ImageDraw.Draw(vignette)
    pad_x = int(frame.size[0] * 0.02)
    pad_y = int(frame.size[1] * 0.02)
    draw.ellipse([pad_x, pad_y, frame.size[0] - pad_x, frame.size[1] - pad_y], fill=255)
    vignette = vignette.filter(ImageFilter.GaussianBlur(radius=max(24, min(frame.size) // 10)))
    edge = Image.new("RGB", frame.size, (16, 12, 8))
    frame = Image.composite(frame, edge, vignette)
    accent = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    ad = ImageDraw.Draw(accent)
    aw, ah = frame.size
    ad.ellipse([int(aw * 0.50), int(ah * 0.55), int(aw * 1.20), int(ah * 1.30)], fill=(255, 140, 0, 42))
    accent = accent.filter(ImageFilter.GaussianBlur(radius=48))
    return Image.alpha_composite(frame.convert("RGBA"), accent).convert("RGB")


def aplicar(ventana, estilo: str = "hub"):
    """Fondo en Canvas (permite letreros sin caja negra encima)."""
    try:
        if not ventana.winfo_exists():
            return
    except Exception:
        return

    state = getattr(ventana, "_cb_fondo", None)
    if state is None:
        canvas = tk.Canvas(ventana, highlightthickness=0, bd=0, bg="#1A120C")
        canvas.place(x=0, y=0, relwidth=1, relheight=1)
        try:
            canvas.lower()
        except Exception:
            pass
        state = {
            "canvas": canvas,
            "estilo": estilo,
            "photo": None,
            "job": None,
            "last": (0, 0),
            "letreros": {},  # tag -> dict specs
        }
        ventana._cb_fondo = state

        def _on_cfg(_e=None):
            _programar(ventana)

        canvas.bind("<Configure>", _on_cfg)
        ventana.bind("<Configure>", _on_cfg, add="+")
    else:
        state["estilo"] = estilo
        try:
            state["canvas"].lower()
        except Exception:
            pass

    ventana.after(30, lambda: _redibujar(ventana, force=True))
    ventana.after(200, lambda: _redibujar(ventana, force=True))


def _programar(ventana):
    state = getattr(ventana, "_cb_fondo", None)
    if not state:
        return
    if state.get("job") is not None:
        try:
            ventana.after_cancel(state["job"])
        except Exception:
            pass
    state["job"] = ventana.after(90, lambda: _redibujar(ventana, force=False))


def _font_tuple(font) -> tuple:
    if isinstance(font, tuple):
        return font
    return ("Segoe UI", 14, "bold")


def _dibujar_letreros(canvas: tk.Canvas, letreros: dict):
    canvas.delete("cb_texto")
    for spec in letreros.values():
        x, y = spec["x"], spec["y"]
        text = spec["text"]
        fill = spec.get("fill", "#FFFFFF")
        font = _font_tuple(spec.get("font"))
        anchor = spec.get("anchor", "nw")
        opts = {
            "text": text,
            "font": font,
            "anchor": anchor,
            "justify": spec.get("justify", "left"),
            "tags": ("cb_texto",),
        }
        w = int(spec.get("width") or 0)
        if w > 0:
            opts["width"] = w
        canvas.create_text(x + 2, y + 2, fill="#1A0F08", **opts)
        canvas.create_text(x, y, fill=fill, **opts)


def _redibujar(ventana, force: bool = False):
    state = getattr(ventana, "_cb_fondo", None)
    if not state:
        return
    try:
        if not ventana.winfo_exists():
            return
    except Exception:
        return

    canvas = state["canvas"]
    w = max(ventana.winfo_width(), canvas.winfo_width(), 2)
    h = max(ventana.winfo_height(), canvas.winfo_height(), 2)
    if w < 80 or h < 80:
        return
    if (
        not force
        and state["last"] == (w, h)
        and state.get("photo") is not None
        and state.get("drawn_estilo") == state["estilo"]
    ):
        # Solo refrescar textos si cambió algo pequeño
        _dibujar_letreros(canvas, state.get("letreros", {}))
        try:
            canvas.lower()
        except Exception:
            pass
        canvas.tag_raise("cb_texto")
        return

    img = preparar(state["estilo"], w, h)
    if img is None:
        return
    photo = ImageTk.PhotoImage(img)
    state["photo"] = photo
    state["last"] = (w, h)
    state["drawn_estilo"] = state["estilo"]
    canvas.delete("cb_img")
    canvas.create_image(0, 0, anchor="nw", image=photo, tags=("cb_img",))
    _dibujar_letreros(canvas, state.get("letreros", {}))
    try:
        canvas.lower()
    except Exception:
        pass
    canvas.tag_raise("cb_texto")


def letrero(
    ventana,
    tag: str,
    text: str,
    x: int,
    y: int,
    *,
    fill: str = "#FFFFFF",
    font=("Segoe UI", 22, "bold"),
    anchor: str = "nw",
    width: int = 0,
    justify: str = "left",
):
    """
    Texto sin contenedor (sobre la foto). Actualiza si el tag ya existe.
    fill recomendados: #FFFFFF, #FFE8CC, #FFB347 (naranja claro)
    """
    state = getattr(ventana, "_cb_fondo", None)
    if not state:
        aplicar(ventana)
        state = ventana._cb_fondo
    state["letreros"][tag] = {
        "text": text,
        "x": int(x),
        "y": int(y),
        "fill": fill,
        "font": font,
        "anchor": anchor,
        "width": int(width) if width else 0,
        "justify": justify,
    }
    canvas = state["canvas"]
    _dibujar_letreros(canvas, state["letreros"])
    try:
        canvas.lower()
    except Exception:
        pass
    canvas.tag_raise("cb_texto")


def quitar_letrero(ventana, tag: str):
    state = getattr(ventana, "_cb_fondo", None)
    if not state:
        return
    state["letreros"].pop(tag, None)
    _dibujar_letreros(state["canvas"], state["letreros"])


def asegurar_al_fondo(ventana):
    state = getattr(ventana, "_cb_fondo", None)
    if not state:
        return
    try:
        state["canvas"].lower()
        state["canvas"].tag_raise("cb_texto")
    except Exception:
        pass


def labels_transparantes(parent):
    """Marca Labels CTk hijos como transparentes (dentro de paneles opacos está bien)."""
    try:
        for child in parent.winfo_children():
            try:
                if child.winfo_class() in ("CTkLabel", "Label") or child.__class__.__name__ == "CTkLabel":
                    child.configure(fg_color="transparent")
            except Exception:
                pass
            labels_transparantes(child)
    except Exception:
        pass
