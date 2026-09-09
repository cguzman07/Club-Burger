import os
import win32print
import win32ui
from PIL import Image, ImageWin
from datetime import datetime
import fechahora as fh

FACTURA_FILE = "numero_factura.txt"
PRINTER_NAME = "POS-58"
_BASE = os.path.dirname(os.path.abspath(__file__))
# Preferir logo térmico en raíz; fallback a assets (Club Burger)
_LOGO_CANDIDATES = (
    os.path.join(_BASE, "logo.bmp.png"),
    os.path.join(_BASE, "assets", "logo_ticket.png"),
    os.path.join(_BASE, "assets", "club_burger_logo.png"),
)
LOGO_PATH = next((p for p in _LOGO_CANDIDATES if os.path.exists(p)), _LOGO_CANDIDATES[0])

# ------------------------------
# Funciones auxiliares de factura
# ------------------------------

def obtener_numero_factura():
    if os.path.exists(FACTURA_FILE):
        with open(FACTURA_FILE, "r") as f:
            try:
                return int(f.read().strip())
            except ValueError:
                return 1
    else:
        return 1

def guardar_numero_factura(numero_factura):
    with open(FACTURA_FILE, "w") as f:
        f.write(str(numero_factura))

# ------------------------------
# Función principal de impresión
# ------------------------------

def imprimir_ticket_real(carrito, total, metodo_pago, recibido, cambio):
    numero_factura = obtener_numero_factura()

    try:
        # Crear contexto de impresión (un solo trabajo)
        pdc = win32ui.CreateDC()
        pdc.CreatePrinterDC(PRINTER_NAME)
        pdc.StartDoc("Factura Club Burger")
        pdc.StartPage()

        y = 0

        # ------------------------------
        # 🔹 1. Imprimir el logo centrado
        # ------------------------------
        if os.path.exists(LOGO_PATH):
            logo = Image.open(LOGO_PATH).convert("L")
            TARGET_WIDTH = 210
            ratio = TARGET_WIDTH / logo.width
            logo = logo.resize((TARGET_WIDTH, int(logo.height * ratio)))

            MAX_WIDTH = 384
            x_offset = int((MAX_WIDTH - logo.width) / 2)
            dib = ImageWin.Dib(logo)
            dib.draw(pdc.GetHandleOutput(),
                     (x_offset, y, x_offset + logo.width, y + logo.height))
            y += logo.height + 10  # espacio después del logo

        # ------------------------------
        # 🔹 2. Texto del ticket
        # ------------------------------
        font = win32ui.CreateFont({
            "name": "Consolas",
            "height": 35,
            "weight": 400,
        })
        pdc.SelectObject(font)

        salto = 30

        def draw(texto):
            nonlocal y
            pdc.TextOut(10, y, texto)
            y += salto

        draw("      Club Burger")
        draw("")
        
        font = win32ui.CreateFont({
            "name": "Consolas",
            "height": 28,
            "weight": 400,
        })
        pdc.SelectObject(font)
        
        draw("        Campo  Alegre")
        draw("   Calle 110 Oeste #33-20")
        draw(" Cel: 3126882478- 3104425058")
        draw("------------------------------")
        draw(f"Factura N° {numero_factura}")
        draw(f"Fecha: {fh.datetime_sql()}")
        draw("------------------------------")
        draw("Cant  Producto       Precio")
        for item in carrito:
            nombre = item[1][:12].ljust(12)
            precio = item[2]
            cant = item[3]
            nota = (item[4] if len(item) > 4 else "") or ""
            subtotal = precio * cant
            draw(f"{cant:<4} {nombre}    ${subtotal:,.0f}")
            if nota.strip():
                # Nota corta bajo el producto (sin salsa, sin queso, etc.)
                draw(f"     * {nota.strip()[:26]}")
        draw("------------------------------")
        font = win32ui.CreateFont({
            "name": "Consolas",
            "height": 30,
            "weight": 400,
        })
        pdc.SelectObject(font)
        draw(f"TOTAL:          ${total:,.0f}")
        font = win32ui.CreateFont({
            "name": "Consolas",
            "height": 28,
            "weight": 400,
        })
        pdc.SelectObject(font)
        draw(f"PAGO:           {metodo_pago}")

        # Pagos parciales
        if isinstance(recibido, dict):
            total_recibido = 0
            for metodo, valor in recibido.items():
                draw(f"{metodo:<14}${valor:,.0f}")
                total_recibido += valor
            draw(f"TOTAL RECIBIDO: ${total_recibido:,.0f}")
            draw(f"CAMBIO:         ${float(cambio):,.0f}")
        else:
            draw(f"RECIBIDO:       ${float(recibido):,.0f}")
            draw(f"CAMBIO:         ${float(cambio):,.0f}")

        draw("------------------------------")
        draw("    ¡Gracias por su compra!")

        # Finalizar impresión
        pdc.EndPage()
        pdc.EndDoc()
        pdc.DeleteDC()

        guardar_numero_factura(numero_factura + 1)

        print("🖨️ Ticket con logo impreso correctamente.")

    except Exception as e:
        print("Error al imprimir:", e)


def enviar_a_impresora(texto):
    printer_name = "POS-58"

    try:
        pdc = win32ui.CreateDC()
        pdc.CreatePrinterDC(printer_name)
        pdc.StartDoc("Reporte Diario")
        pdc.StartPage()

        font = win32ui.CreateFont({
            "name": "Consolas",
            "height": 28,
            "weight": 400,
        })
        pdc.SelectObject(font)

        y = 10
        salto = 30

        for linea in texto.splitlines():
            pdc.TextOut(10, y, linea)
            y += salto

        pdc.EndPage()
        pdc.EndDoc()
        pdc.DeleteDC()

    except Exception as e:
        print("Error al imprimir el reporte:", e)


# ------------------------------
# Ejemplo de uso
# ------------------------------

if __name__ == "__main__":
    carrito = [
        (1, "Hamburguesa", 12000, 2),
        (2, "Papas", 5000, 1),
        (3, "Gaseosa", 3000, 2),
    ]
    imprimir_ticket_real(carrito, total=35000, metodo_pago="Efectivo", recibido=40000, cambio=5000)
