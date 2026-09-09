"""Impresión de tickets en la impresora del restaurante (GDI, mismo estilo del POS)."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

APP_ROOT = Path(__file__).resolve().parent.parent


def _printer_name() -> str:
    for nombre in ("impresora_seleccionada.txt", "impresora.txt"):
        path = APP_ROOT / nombre
        if path.is_file():
            texto = path.read_text(encoding="utf-8", errors="ignore").strip()
            if texto:
                return texto
    try:
        import win32print

        return str(win32print.GetDefaultPrinter())
    except Exception:
        return ""


def _logo_path() -> Path | None:
    candidatos = [
        APP_ROOT / "logo.bmp.png",
        APP_ROOT / "_internal" / "assets" / "logo_ticket.png",
        APP_ROOT / "panel_dueno" / "static" / "logo.png",
    ]
    for path in candidatos:
        if path.is_file():
            return path
    return None


def _dinero(valor: float) -> str:
    entero = int(round(float(valor)))
    return "$ " + f"{entero:,}".replace(",", ".")


def _lineas_ticket(
    detalle: list[dict[str, Any]],
    total: float,
    metodo_pago: str,
    recibido: float | None,
    cambio: float | None,
    factura: int,
    cajero: str,
) -> list[str]:
    ahora = datetime.now().strftime("%d/%m/%Y  %H:%M")
    lineas = [
        "CLUB BURGER",
        "Pedido remoto",
        f"Factura No. {factura}",
        ahora,
        f"Atiende: {cajero or '—'}",
        "-" * 28,
    ]
    for item in detalle:
        lineas.append(f"{item['cantidad']} x {item['nombre']}")
        lineas.append(f"          {_dinero(item['subtotal'])}")
    lineas.extend(
        [
            "-" * 28,
            f"TOTAL     {_dinero(total)}",
            str(metodo_pago),
        ]
    )
    if recibido is not None:
        lineas.append(f"Recibido  {_dinero(recibido)}")
    if cambio is not None:
        lineas.append(f"Cambio    {_dinero(cambio)}")
    lineas.extend(["-" * 28, "Gracias por su compra", ""])
    return lineas


def imprimir_ticket(
    detalle: list[dict[str, Any]],
    total: float,
    metodo_pago: str,
    recibido: float | None,
    cambio: float | None,
    factura: int,
    cajero: str,
) -> tuple[bool, str | None]:
    if os.environ.get("PANEL_NO_PRINT") == "1":
        return False, "Impresión desactivada en pruebas"
    printer = _printer_name()
    if not printer:
        return False, "No hay impresora configurada en Windows"
    texto = _lineas_ticket(detalle, total, metodo_pago, recibido, cambio, factura, cajero)
    try:
        _imprimir_gdi(printer, texto)
        return True, None
    except Exception as exc:
        try:
            _imprimir_raw(printer, texto)
            return True, None
        except Exception as exc2:
            return False, str(exc2) or str(exc)


def _dibujar_logo(pdc, y: int = 8) -> int:
    logo = _logo_path()
    if not logo:
        return y
    try:
        from PIL import Image, ImageWin

        img = Image.open(logo)
        w, h = img.size
        scale = min(200 / max(w, 1), 80 / max(h, 1), 1.0)
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
        if (nw, nh) != (w, h):
            img = img.resize((nw, nh), Image.Resampling.LANCZOS)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        dib = ImageWin.Dib(img)
        x = max(0, (280 - nw) // 2)
        dib.draw(pdc.GetHandleOutput(), (x, y, x + nw, y + nh))
        return y + nh + 8
    except Exception:
        return y


def _imprimir_gdi(printer: str, lineas: list[str]) -> None:
    import win32ui

    pdc = win32ui.CreateDC()
    pdc.CreatePrinterDC(printer)
    pdc.StartDoc("Club Burger")
    pdc.StartPage()
    y = _dibujar_logo(pdc)
    font = win32ui.CreateFont({"name": "Consolas", "height": 26, "weight": 400})
    pdc.SelectObject(font)
    for linea in lineas:
        pdc.TextOut(12, y, linea)
        y += 28
    pdc.EndPage()
    pdc.EndDoc()
    pdc.DeleteDC()


def _imprimir_raw(printer: str, lineas: list[str]) -> None:
    import win32print

    payload = ("\r\n".join(lineas) + "\r\n\r\n\r\n").encode("cp850", "replace")
    handle = win32print.OpenPrinter(printer)
    try:
        win32print.StartDocPrinter(handle, 1, ("Club Burger", None, "RAW"))
        win32print.StartPagePrinter(handle)
        win32print.WritePrinter(handle, payload)
        win32print.EndPagePrinter(handle)
        win32print.EndDocPrinter(handle)
    finally:
        win32print.ClosePrinter(handle)
