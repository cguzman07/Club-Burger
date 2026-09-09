import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import customtkinter as ctk

from ventana_fiados import ventana_ver_fiados
from database import consultar_todos, obtener_caja_abierta, consultar_uno
from reportes_impresion import (
    armar_texto_reporte_diario,
    armar_texto_reporte_mensual,
    armar_texto_reporte_rango,
    imprimir_texto,
    totales_por_sesion,
)
import tema_caja as tema
import responsive as resp
import animaciones as anim
import fechahora as fh
from iconos import apply_window_icon
import fondos


def es_fecha_valida(fecha_str):
    try:
        datetime.strptime(fecha_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def ventana_reportes(usuario, ventana_principal):
    ventana_principal.withdraw()
    tema.apply_theme()
    tema.style_treeview()

    ventana = ctk.CTkToplevel()
    ventana.title("Reportes del Sistema POS")
    ventana.configure(fg_color="#1A120C")
    apply_window_icon(ventana)
    fondos.aplicar(ventana, estilo="reportes")
    resp.fit_fullscreenish(ventana, margin=0.03)
    ventana.after(100, lambda: fondos.asegurar_al_fondo(ventana))
    ventana.after(150, lambda: fondos.labels_transparantes(ventana))

    def styled_button(parent, text, bg_color, command=None, **kwargs):
        return tema.button(parent, text, bg_color, command=command, height=42, **kwargs)

    def volver_al_menu():
        ventana.destroy()
        ventana_principal.deiconify()

    def mostrar_menu_reportes():
        for widget in ventana.winfo_children():
            widget.destroy()

        header = ctk.CTkFrame(ventana, fg_color=tema.BG_PANEL, corner_radius=0, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)
        btn_volver = styled_button(header, "← Volver", tema.ACCENT_GRAY, command=volver_al_menu, width=110)
        btn_volver.pack(side="left", padx=16, pady=14)
        title_lbl = tema.label(header, "Reportes", font=tema.FONT_TITLE)
        title_lbl.pack(side="left", padx=8)

        frame = tema.card(ventana)
        frame.pack(expand=True, fill="both", padx=40, pady=40)

        tema.label(frame, "Seleccione un tipo de reporte", font=tema.FONT_HEADER).pack(pady=(28, 20))

        report_btns = []
        for text, color, cmd in [
            ("📅  Reporte de turno", tema.ACCENT_GREEN, mostrar_reporte_diario),
            ("🗓️  Reporte Mensual", tema.ACCENT_BLUE, mostrar_reporte_mensual),
            ("📊  Reporte por Rango", tema.ACCENT_PURPLE, mostrar_reporte_rango),
            ("📋  Ver Fiados", tema.ACCENT_ORANGE, lambda: ventana_ver_fiados(ventana)),
        ]:
            b = styled_button(frame, text, color, command=cmd, height=48)
            b.pack(fill="x", padx=80, pady=8)
            report_btns.append(b)

        ctk.CTkFrame(frame, fg_color="transparent", height=20).pack()

        anim.soft_entrance(
            ventana,
            title=title_lbl,
            panels=[frame],
            buttons=[btn_volver] + report_btns,
            accent=tema.ACCENT_ORANGE,
        )

    def mostrar_reporte_diario():
        for widget in ventana.winfo_children():
            widget.destroy()

        header = ctk.CTkFrame(ventana, fg_color=tema.BG_PANEL, corner_radius=0, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)
        styled_button(header, "← Volver", tema.ACCENT_GRAY, command=mostrar_menu_reportes, width=110).pack(
            side="left", padx=16, pady=14
        )
        tema.label(header, "Reporte de turno (caja)", font=tema.FONT_TITLE).pack(side="left", padx=8)

        panel = tema.panel(ventana)
        panel.pack(fill="both", expand=True, padx=16, pady=16)

        # Sesión actual abierta, o la última del usuario
        sesion = obtener_caja_abierta(usuario)
        if not sesion:
            try:
                sesion = consultar_uno(
                    """
                    SELECT id, usuario, fecha, hora_apertura, hora_cierre, capital_inicial,
                           capital_final, total_ventas, fecha_cierre
                    FROM caja WHERE usuario = ?
                    ORDER BY id DESC LIMIT 1
                    """,
                    (usuario,),
                )
            except Exception:
                sesion = consultar_uno(
                    """
                    SELECT id, usuario, fecha, hora_apertura, hora_cierre, capital_inicial,
                           capital_final, total_ventas
                    FROM caja WHERE usuario = ?
                    ORDER BY id DESC LIMIT 1
                    """,
                    (usuario,),
                )

        if not sesion:
            tema.label(
                panel,
                "No hay sesiones de caja. Abre caja para generar el reporte de turno.",
                font=tema.FONT_BODY,
                color=tema.TEXT_DIM,
            ).pack(pady=24)
            styled_button(ventana, "← Volver", tema.ACCENT_GRAY, command=mostrar_menu_reportes).pack(
                pady=(0, 16)
            )
            return

        id_caja = sesion["id"]
        cierre = sesion["hora_cierre"]
        fecha_ci = sesion["fecha_cierre"] if "fecha_cierre" in sesion.keys() else None
        if cierre:
            periodo = f"Apertura {sesion['fecha']} {sesion['hora_apertura']}  →  Cierre {(fecha_ci or sesion['fecha'])} {cierre}"
        else:
            periodo = f"Apertura {sesion['fecha']} {sesion['hora_apertura']}  →  (en curso)"

        tema.label(panel, f"Caja #{id_caja}  ·  {periodo}", font=tema.FONT_BODY, color=tema.ACCENT_ORANGE).pack(
            anchor="w", padx=8, pady=(4, 8)
        )
        tema.label(
            panel,
            "Totales desde que abriste hasta que cierres (no por día calendario).",
            font=tema.FONT_SMALL,
            color=tema.TEXT_DIM,
        ).pack(anchor="w", padx=8, pady=(0, 8))

        host = tk.Frame(panel, bg=tema.BG_PANEL)
        host.pack(fill="both", expand=True, padx=8, pady=8)

        columnas = (
            "ID",
            "Producto",
            "Nota",
            "Cantidad",
            "Precio Unitario",
            "Total",
            "Método de Pago",
            "Fecha",
        )
        tabla = ttk.Treeview(host, columns=columnas, show="headings", style="Dark.Treeview")
        for col in columnas:
            tabla.heading(col, text=col)
            tabla.column(col, width=100)
        tabla.column("Nota", width=120)
        tabla.column("Producto", width=130)
        tabla.pack(expand=True, fill="both")

        try:
            ventas_turno = consultar_todos(
                """
                SELECT id, nombre_producto, nota, cantidad, precio_unitario, total, metodo_pago, fecha
                FROM ventas
                WHERE id_caja = ?
                ORDER BY id
                """,
                (id_caja,),
            )
        except Exception:
            ventas_turno = consultar_todos(
                """
                SELECT id, nombre_producto, cantidad, precio_unitario, total, metodo_pago, fecha
                FROM ventas
                WHERE id_caja = ?
                ORDER BY id
                """,
                (id_caja,),
            )

        total_general = 0
        for venta in ventas_turno:
            nota = ""
            try:
                nota = venta["nota"] or ""
            except Exception:
                nota = ""
            tabla.insert(
                "",
                tk.END,
                values=(
                    venta["id"],
                    venta["nombre_producto"],
                    nota,
                    venta["cantidad"],
                    f"{venta['precio_unitario']:,.2f}",
                    f"{venta['total']:,.2f}",
                    venta["metodo_pago"],
                    venta["fecha"],
                ),
            )
            total_general += venta["total"]

        import sqlite3

        conn = sqlite3.connect("datos_pos.db")
        try:
            _, por_metodo = totales_por_sesion(conn.cursor(), id_caja)
        finally:
            conn.close()

        resumen = tema.card(ventana)
        resumen.pack(fill="x", padx=16, pady=(0, 8))
        tema.label(resumen, "Ingresos del turno por método de pago", font=tema.FONT_HEADER).pack(
            anchor="w", padx=16, pady=(12, 6)
        )

        if not por_metodo:
            tema.label(resumen, "(sin ventas en este turno)", font=tema.FONT_BODY, color=tema.TEXT_DIM).pack(
                anchor="w", padx=16
            )
        else:
            for metodo, total in por_metodo:
                tema.label(
                    resumen,
                    f"{metodo}: ${float(total):,.2f}",
                    font=tema.FONT_BODY,
                    color=tema.TEXT_DIM,
                ).pack(anchor="w", padx=16)

        tema.label(
            resumen,
            f"Total vendido en el turno: ${total_general:,.2f}",
            font=tema.FONT_BODY_BOLD,
            color=tema.ACCENT_GREEN,
        ).pack(anchor="w", padx=16, pady=(8, 12))

        def imprimir_diario():
            texto = armar_texto_reporte_diario(usuario, id_caja=id_caja)
            imprimir_texto(texto)

        styled_button(ventana, "🖨  Imprimir reporte de turno", tema.ACCENT_TEAL, command=imprimir_diario).pack(
            pady=(0, 16)
        )

    def mostrar_reporte_mensual():
        for widget in ventana.winfo_children():
            widget.destroy()

        header = ctk.CTkFrame(ventana, fg_color=tema.BG_PANEL, corner_radius=0, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)
        styled_button(header, "← Volver", tema.ACCENT_GRAY, command=mostrar_menu_reportes, width=110).pack(
            side="left", padx=16, pady=14
        )
        tema.label(header, "Reporte Mensual", font=tema.FONT_TITLE).pack(side="left", padx=8)

        selector = tema.card(ventana)
        selector.pack(fill="x", padx=16, pady=12)
        row = ctk.CTkFrame(selector, fg_color="transparent")
        row.pack(padx=16, pady=12)
        tema.label(row, "Mes (YYYY-MM):", font=tema.FONT_BODY, color=tema.TEXT_DIM).pack(side="left", padx=6)

        hoy = fh.ahora()
        meses = []
        for i in range(12):
            año = hoy.year
            mes_num = hoy.month - i
            while mes_num <= 0:
                mes_num += 12
                año -= 1
            meses.append(f"{año:04d}-{mes_num:02d}")

        combomes = ctk.CTkComboBox(
            row,
            values=meses,
            width=140,
            height=36,
            fg_color=tema.BG_INPUT,
            border_width=0,
            button_color=tema.ACCENT_ORANGE,
            corner_radius=tema.RADIUS_SM,
        )
        combomes.pack(side="left")
        combomes.set(fh.ano_mes_sql())

        frame_grafico = tema.panel(ventana)
        frame_grafico.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        def generar_y_mostrar():
            for widget in frame_grafico.winfo_children():
                widget.destroy()

            mes_seleccionado = combomes.get()
            datos = consultar_todos(
                """
                SELECT fecha, nombre_producto, SUM(cantidad) as cantidad_total, SUM(total) as total_producto
                FROM ventas
                WHERE fecha LIKE ?
                GROUP BY fecha, nombre_producto
                """,
                (f"{mes_seleccionado}%",),
            )

            if not datos:
                tema.label(
                    frame_grafico,
                    "No hay datos de ventas este mes.",
                    color=tema.ACCENT_RED,
                ).pack(pady=24)
                return

            ventas_por_dia = {}
            producto_mas_vendido = {}

            for row_data in datos:
                fecha = row_data["fecha"]
                producto = row_data["nombre_producto"]
                cantidad = row_data["cantidad_total"]
                dia = fecha.split(" ")[0]
                ventas_por_dia[dia] = ventas_por_dia.get(dia, 0) + cantidad
                producto_mas_vendido[producto] = producto_mas_vendido.get(producto, 0) + cantidad

            fig, axs = plt.subplots(2, 1, figsize=(7, 6))
            dias = sorted(ventas_por_dia.keys())
            cantidades = [ventas_por_dia[d] for d in dias]

            axs[0].bar(dias, cantidades, color=tema.ACCENT_ORANGE)
            axs[0].set_title("Ventas por Día del Mes")
            axs[0].tick_params(axis="x", rotation=45)

            productos = list(producto_mas_vendido.keys())
            ventas = list(producto_mas_vendido.values())

            axs[1].barh(productos, ventas, color=tema.ACCENT_BLUE)
            axs[1].set_title("Productos Más Vendidos del Mes")

            tema.dark_matplotlib(fig, axs)
            plt.tight_layout()
            canvas = FigureCanvasTkAgg(fig, master=frame_grafico)
            canvas.draw()
            canvas.get_tk_widget().configure(bg=tema.BG_PANEL)
            canvas.get_tk_widget().pack(pady=10, fill="both", expand=True)

        generar_y_mostrar()

        actions = ctk.CTkFrame(ventana, fg_color="transparent")
        actions.pack(pady=(0, 14))
        styled_button(actions, "Actualizar", tema.ACCENT_GREEN, command=generar_y_mostrar).pack(
            side="left", padx=6
        )

        def imprimir_mensual():
            mes = combomes.get()
            texto = armar_texto_reporte_mensual(usuario, mes)
            imprimir_texto(texto)

        styled_button(actions, "🖨  Imprimir", tema.ACCENT_TEAL, command=imprimir_mensual).pack(
            side="left", padx=6
        )

    def mostrar_reporte_rango():
        for widget in ventana.winfo_children():
            widget.destroy()

        header = ctk.CTkFrame(ventana, fg_color=tema.BG_PANEL, corner_radius=0, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)
        styled_button(header, "← Volver", tema.ACCENT_GRAY, command=mostrar_menu_reportes, width=110).pack(
            side="left", padx=16, pady=14
        )
        tema.label(header, "Reporte por Rango", font=tema.FONT_TITLE).pack(side="left", padx=8)

        frame_rango = tema.card(ventana)
        frame_rango.pack(fill="x", padx=16, pady=12)

        row = ctk.CTkFrame(frame_rango, fg_color="transparent")
        row.pack(padx=16, pady=12)

        tema.label(row, "Inicio (YYYY-MM-DD):", font=tema.FONT_SMALL, color=tema.TEXT_DIM).grid(
            row=0, column=0, padx=5, sticky="w"
        )
        entrada_inicio = tema.entry(row, width=140)
        entrada_inicio.grid(row=1, column=0, padx=5, pady=4)

        tema.label(row, "Fin (YYYY-MM-DD):", font=tema.FONT_SMALL, color=tema.TEXT_DIM).grid(
            row=0, column=1, padx=5, sticky="w"
        )
        entrada_fin = tema.entry(row, width=140)
        entrada_fin.grid(row=1, column=1, padx=5, pady=4)

        frame_resultado = tema.panel(ventana)
        frame_resultado.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        def generar_reporte():
            for widget in frame_resultado.winfo_children():
                widget.destroy()

            inicio = entrada_inicio.get().strip()
            fin = entrada_fin.get().strip()

            if not es_fecha_valida(inicio) or not es_fecha_valida(fin):
                messagebox.showerror("Error", "Las fechas deben estar en formato YYYY-MM-DD")
                return

            fecha_inicio = datetime.strptime(inicio, "%Y-%m-%d").date()
            fecha_fin = datetime.strptime(fin, "%Y-%m-%d").date()

            if fecha_inicio > fecha_fin:
                messagebox.showwarning(
                    "Advertencia",
                    "La fecha de inicio no puede ser mayor a la fecha de fin.",
                )
                return

            datos = consultar_todos(
                """
                SELECT fecha, nombre_producto, SUM(cantidad) as cantidad_total, SUM(total) as total_producto
                FROM ventas
                WHERE substr(fecha,1,10) BETWEEN ? AND ?
                GROUP BY fecha, nombre_producto
                """,
                (inicio, fin),
            )

            if not datos:
                tema.label(frame_resultado, "No hay ventas en ese rango.", color=tema.ACCENT_RED).pack(
                    pady=16
                )
                return

            ventas_por_dia = {}
            producto_mas_vendido = {}

            for row_data in datos:
                fecha = row_data["fecha"]
                producto = row_data["nombre_producto"]
                cantidad = row_data["cantidad_total"]
                dia = fecha.split(" ")[0]
                ventas_por_dia[dia] = ventas_por_dia.get(dia, 0) + cantidad
                producto_mas_vendido[producto] = producto_mas_vendido.get(producto, 0) + cantidad

            fig, axs = plt.subplots(2, 1, figsize=(7, 6))
            dias = sorted(ventas_por_dia.keys())
            cantidades = [ventas_por_dia[d] for d in dias]

            axs[0].bar(dias, cantidades, color=tema.ACCENT_ORANGE)
            axs[0].set_title("Ventas por Día")
            axs[0].tick_params(axis="x", rotation=45)

            productos = list(producto_mas_vendido.keys())
            ventas = list(producto_mas_vendido.values())

            axs[1].barh(productos, ventas, color=tema.ACCENT_PURPLE)
            axs[1].set_title("Productos Más Vendidos")

            tema.dark_matplotlib(fig, axs)
            plt.tight_layout()
            canvas = FigureCanvasTkAgg(fig, master=frame_resultado)
            canvas.draw()
            canvas.get_tk_widget().configure(bg=tema.BG_PANEL)
            canvas.get_tk_widget().pack(pady=10, fill="both", expand=True)

        actions = ctk.CTkFrame(ventana, fg_color="transparent")
        actions.pack(pady=(0, 14))
        styled_button(actions, "Generar Reporte", tema.ACCENT_GREEN, command=generar_reporte).pack(
            side="left", padx=6
        )

        def imprimir_rango():
            inicio = entrada_inicio.get().strip()
            fin = entrada_fin.get().strip()
            texto = armar_texto_reporte_rango(usuario, inicio, fin)
            imprimir_texto(texto)

        styled_button(actions, "🖨  Imprimir", tema.ACCENT_TEAL, command=imprimir_rango).pack(
            side="left", padx=6
        )

    mostrar_menu_reportes()
