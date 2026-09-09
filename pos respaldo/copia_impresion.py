import win32print
import win32ui
from datetime import datetime
import os

FACTURA_FILE = "numero_factura.txt"

def obtener_numero_factura():
    """Lee el número actual desde un archivo, o crea el archivo si no existe."""
    if os.path.exists(FACTURA_FILE):
        with open(FACTURA_FILE, "r") as f:
            try:
                return int(f.read().strip())
            except ValueError:
                return 1
    else:
        return 1

def guardar_numero_factura(numero_factura):
    """Guarda el nuevo número de factura en el archivo."""
    with open(FACTURA_FILE, "w") as f:
        f.write(str(numero_factura))

def imprimir_ticket_real(carrito, total, metodo_pago, recibido, cambio):
    numero_factura = obtener_numero_factura()
    printer_name = "POS-58"  # Cambia por el nombre correcto de tu impresora
    cajon_command = b'\x1B\x70\x00\x19\xFA'  # Código para abrir cajón

    try:
        # Abrir cajón
        hprinter = win32print.OpenPrinter(printer_name)
        win32print.StartDocPrinter(hprinter, 1, ("Ticket", None, "RAW"))
        win32print.StartPagePrinter(hprinter)
        win32print.WritePrinter(hprinter, cajon_command)
        win32print.EndPagePrinter(hprinter)
        win32print.EndDocPrinter(hprinter)
        win32print.ClosePrinter(hprinter)

        # Crear DC para imprimir texto
        pdc = win32ui.CreateDC()
        pdc.CreatePrinterDC(printer_name)
        pdc.StartDoc("Factura")
        pdc.StartPage()

        font = win32ui.CreateFont({
            "name": "Consolas",
            "height": 35,
            "weight": 400,
        })
        pdc.SelectObject(font)

        y = 10
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
        draw(datetime.now().strftime("Fecha: %Y-%m-%d %H:%M:%S"))
        draw("------------------------------")
        draw("Cant  Producto       Precio")
        for item in carrito:
            nombre = item[1][:12].ljust(12)
            precio = item[2]
            cant = item[3]
            subtotal = precio * cant
            draw(f"{cant:<4} {nombre}    ${subtotal:,.0f}")
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

        # Soporte para pagos parciales
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

        pdc.EndPage()
        pdc.EndDoc()
        pdc.DeleteDC()

        # Guardar el siguiente número para la próxima factura
        guardar_numero_factura(numero_factura + 1)

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

