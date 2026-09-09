"""Aplica el icono Club Burger a ventanas Tk / CustomTkinter."""
from __future__ import annotations

import os

from paths import icon_ico_path, logo_ui_path


def apply_window_icon(ventana) -> None:
    """Icono en barra de título y barra de tareas (Windows)."""
    ico = icon_ico_path()
    if not os.path.exists(ico):
        return
    try:
        # CTk: marca que ya se setea icono para no sobrescribir con el de CustomTkinter
        ventana.iconbitmap(ico)
    except Exception:
        pass
    try:
        # Taskbar en Windows (algunas builds de CTK)
        ventana.wm_iconbitmap(default=ico)
    except Exception:
        try:
            ventana.iconbitmap(default=ico)
        except Exception:
            pass
    # PhotoImage PNG como refuerzo (taskbar / Alt-Tab en algunos entornos)
    try:
        import tkinter as tk
        from PIL import Image, ImageTk

        png = logo_ui_path()
        if os.path.exists(png):
            img = Image.open(png).convert("RGBA").resize((64, 64))
            photo = ImageTk.PhotoImage(img)
            ventana.iconphoto(True, photo)
            # evitar GC
            if not hasattr(ventana, "_cb_icon_refs"):
                ventana._cb_icon_refs = []
            ventana._cb_icon_refs.append(photo)
    except Exception:
        pass
