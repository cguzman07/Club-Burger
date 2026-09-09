import tkinter as tk
from tkinter import messagebox, simpledialog
from datetime import datetime
import json
import sqlite3
import customtkinter as ctk
from saludos import mostrar_despedida

from impresion import imprimir_ticket_real
from reportes_impresion import armar_texto_reporte_diario, imprimir_texto, efectivo_del_turno
from database import get_connection, ejecutar, consultar_uno, consultar_todos
from database import (
    registrar_fiado,
    obtener_caja_abierta,
    guardar_factura_espera,
    listar_facturas_espera,
    obtener_factura_espera,
    eliminar_factura_espera,
    inicializar_db,
)
import tema_caja as tema
import responsive as resp
import animaciones as anim
import fechahora as fh
from iconos import apply_window_icon
import fondos


def _item_parts(item):
    """Soporta carrito antiguo (4) y con nota (5): id, nombre, precio, cant, nota."""
    if len(item) >= 5:
        return item[0], item[1], item[2], item[3], (item[4] or "").strip()
    return item[0], item[1], item[2], item[3], ""


# ---------- Tema global CustomTkinter (solo visual) ----------
tema.apply_theme()


def obtener_numero_factura():
    conn = sqlite3.connect("datos_pos.db")
    cursor = conn.cursor()
    cursor.execute("SELECT numero_actual FROM numeracion_factura WHERE id = 1")
    numero = cursor.fetchone()[0]
    conn.close()
    return numero


def incrementar_numero_factura():
    conn = sqlite3.connect("datos_pos.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE numeracion_factura SET numero_actual = numero_actual + 1 WHERE id = 1")
    conn.commit()
    conn.close()


def ventana_caja(usuario, ventana_principal):
    if ventana_principal:
        ventana_principal.withdraw()

    inicializar_db()

    ventana = ctk.CTkToplevel()
    ventana.title("Caja - Punto de Venta")
    ventana.configure(fg_color="#1A120C")
    apply_window_icon(ventana)
    fondos.aplicar(ventana, estilo="caja")
    resp.fit_fullscreenish(ventana, margin=0.018)
    m = resp.metrics(ventana)

    # Referencias UI mutables (misma idea que el archivo original)
    metodo_pago = None
    entrada_dinero = None
    carrito = []
    total_var = tk.DoubleVar(value=0.0)
    seleccion_index = tk.IntVar(value=-1)
    categoria_activa = {"nombre": None}
    botones_categoria = {}
    layout_cols = {"n": m["product_cols"]}

    # ===================== LAYOUT =====================
    # Header con marca + chip usuario + reloj local en vivo
    search_var = tk.StringVar()
    search_holder = {"entry": None}

    def _extra_search(header):
        search_entry = ctk.CTkEntry(
            header,
            textvariable=search_var,
            placeholder_text="Buscar producto…",
            width=m["search_w"],
            height=36,
            corner_radius=tema.RADIUS_SM,
            fg_color=tema.BG_INPUT,
            border_width=0,
            font=tema.FONT_BODY,
        )
        search_entry.pack(side="left", padx=max(10, m["pad"]), pady=10)
        search_holder["entry"] = search_entry

    brand = tema.brand_header(
        ventana,
        usuario=usuario,
        rol="cajero",
        height=m["header_h"],
        show_clock=True,
        extra_left=_extra_search,
    )
    header_title = brand["brand_title"]
    search_entry = search_holder["entry"]

    # Cuerpo 3 columnas (anchos según pantalla)
    body = ctk.CTkFrame(ventana, fg_color="#1A120C", corner_radius=0)
    # Márgenes amplios: se ve comida alrededor de los paneles (elegante, no pared negra)
    _gap = max(14, m["pad"] + 4)
    body.pack(fill="both", expand=True, padx=_gap, pady=_gap)
    ventana.after(80, lambda: fondos.asegurar_al_fondo(ventana))
    ventana.after(300, lambda: fondos.asegurar_al_fondo(ventana))
    ventana.after(120, lambda: fondos.labels_transparantes(ventana))
    body.grid_columnconfigure(0, weight=0, minsize=m["sidebar"])
    body.grid_columnconfigure(1, weight=1)
    body.grid_columnconfigure(2, weight=0, minsize=m["cart"])
    body.grid_rowconfigure(0, weight=1)

    frame_categorias = ctk.CTkScrollableFrame(
        body,
        fg_color=tema.BG_PANEL,
        corner_radius=tema.RADIUS,
        width=m["sidebar"],
    )
    frame_categorias.grid(row=0, column=0, sticky="nsw", padx=(0, max(6, m["pad"] - 2)))

    productos_panel = ctk.CTkFrame(body, fg_color=tema.BG_PANEL, corner_radius=tema.RADIUS)
    productos_panel.grid(row=0, column=1, sticky="nsew", padx=(0, max(6, m["pad"] - 2)))
    productos_panel.grid_rowconfigure(0, weight=1)
    productos_panel.grid_columnconfigure(0, weight=1)

    productos_frame = ctk.CTkScrollableFrame(
        productos_panel,
        fg_color=tema.BG_PANEL,
        corner_radius=tema.RADIUS,
    )
    productos_frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

    # Panel derecho: más ancho (hacia la izquierda) — items arriba, pago y acciones fijos abajo
    panel_carrito = ctk.CTkFrame(
        body,
        fg_color=tema.BG_PANEL,
        corner_radius=tema.RADIUS,
        width=m["cart"],
    )
    panel_carrito.grid(row=0, column=2, sticky="nsew")
    panel_carrito.grid_propagate(False)

    # Estado UI del teclado (persiste entre refrescos del carrito)
    teclado_visible = {"on": False}

    # Orden pack: primero bottoms (acciones → pago), luego header + lista
    acciones_frame = ctk.CTkFrame(panel_carrito, fg_color=tema.BG_PANEL, corner_radius=0)
    acciones_frame.pack(side="bottom", fill="x", padx=6, pady=(2, 6))

    pago_frame = ctk.CTkFrame(panel_carrito, fg_color=tema.BG_PANEL, corner_radius=0)
    pago_frame.pack(side="bottom", fill="x", padx=6, pady=(0, 2))

    header_pedido = ctk.CTkFrame(panel_carrito, fg_color=tema.BG_PANEL, corner_radius=0)
    header_pedido.pack(side="top", fill="x", padx=6, pady=(6, 0))

    frame_carrito = ctk.CTkScrollableFrame(
        panel_carrito,
        fg_color=tema.BG_PANEL,
        corner_radius=tema.RADIUS,
    )
    frame_carrito.pack(side="top", fill="both", expand=True, padx=4, pady=(2, 2))

    # ===================== HELPERS VISUALES =====================
    def styled_button(parent, text, bg_color, command=None, height=40, font=None, **kwargs):
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            fg_color=bg_color,
            hover_color=tema.BG_HOVER,
            text_color=tema.TEXT,
            corner_radius=tema.RADIUS_BTN,
            height=height,
            font=font or tema.FONT_BTN,
            **kwargs,
        )

    def _resaltar_categoria(cat):
        categoria_activa["nombre"] = cat
        for nombre, btn in botones_categoria.items():
            if nombre == cat:
                btn.configure(border_width=3, border_color=tema.ACCENT_ORANGE)
            else:
                btn.configure(border_width=0)

    # ===================== CARRITO (UI) =====================
    def actualizar_carrito():
        nonlocal metodo_pago, entrada_dinero

        # Conservar monto/método al refrescar (p. ej. al abrir el teclado)
        monto_prev = ""
        metodo_prev = "Efectivo"
        try:
            if entrada_dinero is not None:
                monto_prev = entrada_dinero.get() or ""
        except Exception:
            pass
        try:
            if metodo_pago is not None:
                metodo_prev = metodo_pago.get() or "Efectivo"
        except Exception:
            pass

        for widget in frame_carrito.winfo_children():
            widget.destroy()
        for widget in acciones_frame.winfo_children():
            widget.destroy()
        for widget in pago_frame.winfo_children():
            widget.destroy()
        for widget in header_pedido.winfo_children():
            widget.destroy()

        labels_items = []
        alto_ventana = max(ventana.winfo_height(), 1)
        compacto = True  # panel pedido siempre denso para ver más ítems
        tecla_h = 28 if alto_ventana < 780 else 32
        btn_h = 30

        def seleccionar_item(idx):
            seleccion_index.set(idx)
            for i, row in enumerate(labels_items):
                row.configure(
                    fg_color=tema.ACCENT_ORANGE if i == idx else tema.BG_CARD,
                    border_width=2 if i == idx else 0,
                    border_color=tema.ACCENT_ORANGE,
                )

        def eliminar_producto():
            idx = seleccion_index.get()
            if idx != -1 and idx < len(carrito):
                carrito.pop(idx)
                seleccion_index.set(-1)
                actualizar_carrito()

        sesion = obtener_caja_abierta(usuario)
        if sesion:
            estado_txt = f"Abierta · {sesion['fecha']} {sesion['hora_apertura']}"
        else:
            estado_txt = "Sin sesión de caja"

        ctk.CTkLabel(
            header_pedido,
            text="PEDIDO ACTUAL",
            font=tema.FONT_BODY_BOLD,
            text_color=tema.TEXT,
        ).pack(anchor="w", padx=8, pady=(2, 0))
        ctk.CTkLabel(
            header_pedido,
            text=estado_txt,
            font=tema.FONT_SMALL,
            text_color=tema.ACCENT_GREEN if sesion else tema.TEXT_DIM,
        ).pack(anchor="w", padx=8, pady=(0, 2))

        total = 0
        if not carrito:
            ctk.CTkLabel(
                frame_carrito,
                text="(Sin productos)",
                font=tema.FONT_SMALL,
                text_color=tema.TEXT_MUTED,
            ).pack(pady=8)
        else:
            for idx, item in enumerate(carrito):
                _pid, nombre, precio, cantidad, nota = _item_parts(item)
                row = ctk.CTkFrame(
                    frame_carrito,
                    fg_color=tema.BG_CARD,
                    corner_radius=tema.RADIUS_SM,
                    cursor="hand2",
                    height=36,
                )
                row.pack(fill="x", padx=6, pady=1)
                row.pack_propagate(False)

                linea = f"{cantidad}x {nombre}"
                if nota:
                    linea = f"{linea} · {nota}"
                ctk.CTkLabel(
                    row,
                    text=linea[:42],
                    font=tema.FONT_SMALL,
                    text_color=tema.TEXT,
                    anchor="w",
                ).pack(side="left", fill="x", expand=True, padx=(8, 4), pady=4)
                ctk.CTkLabel(
                    row,
                    text=f"${precio * cantidad:,.0f}",
                    font=tema.FONT_SMALL,
                    text_color=tema.ACCENT_ORANGE,
                    anchor="e",
                ).pack(side="right", padx=(4, 8), pady=4)
                row.bind("<Button-1>", lambda e, i=idx: seleccionar_item(i))
                for child in row.winfo_children():
                    child.bind("<Button-1>", lambda e, i=idx: seleccionar_item(i))
                labels_items.append(row)
                total += precio * cantidad

        total_var.set(total)

        # ----- Zona de pago (fija, compacta) -----
        top_pago = ctk.CTkFrame(pago_frame, fg_color="transparent")
        top_pago.pack(fill="x", padx=4, pady=(2, 0))
        ctk.CTkLabel(
            top_pago,
            text="TOTAL",
            font=tema.FONT_SMALL,
            text_color=tema.TEXT_DIM,
        ).pack(side="left", padx=(4, 6))
        ctk.CTkLabel(
            top_pago,
            text=f"${total:,.0f}",
            font=tema.FONT_HEADER,
            text_color=tema.TEXT,
        ).pack(side="left")

        metodo_pago = ctk.CTkComboBox(
            pago_frame,
            values=["Efectivo", "Tarjeta", "Nequi", "Transferencia"],
            font=tema.FONT_SMALL,
            dropdown_font=tema.FONT_SMALL,
            fg_color=tema.BG_INPUT,
            border_width=0,
            button_color=tema.ACCENT_ORANGE,
            button_hover_color=tema.ACCENT_YELLOW,
            corner_radius=tema.RADIUS_SM,
            height=28,
        )
        metodo_pago.pack(padx=6, fill="x", pady=(4, 2))
        try:
            metodo_pago.set(metodo_prev)
        except Exception:
            metodo_pago.set("Efectivo")

        pay_row = ctk.CTkFrame(pago_frame, fg_color="transparent")
        pay_row.pack(fill="x", padx=4, pady=(0, 2))
        for i, (label, color) in enumerate(
            [
                ("Efectivo", tema.ACCENT_GREEN_DARK),
                ("Tarjeta", tema.ACCENT_BLUE),
                ("Nequi", tema.ACCENT_PURPLE),
                ("Transferencia", "#4527A0"),
            ]
        ):
            b = ctk.CTkButton(
                pay_row,
                text=label if label != "Transferencia" else "Transf.",
                fg_color=color,
                hover_color=tema.BG_HOVER,
                corner_radius=tema.RADIUS_SM,
                height=26,
                font=tema.FONT_SMALL,
                command=lambda m=label: metodo_pago.set(m),
            )
            b.grid(row=0, column=i, padx=1, sticky="ew")
            pay_row.grid_columnconfigure(i, weight=1)

        entrada_dinero_var = tk.StringVar()
        cambio_var = tk.StringVar(value="Cambio: $0")

        def calcular_cambio(*args):
            try:
                recibido = float(entrada_dinero_var.get())
                cambio = recibido - total_var.get()
                cambio_var.set(f"Cambio: ${cambio:,.0f}")
            except ValueError:
                cambio_var.set("Monto inválido")

        entrada_dinero_var.trace_add("write", calcular_cambio)

        monto_row = ctk.CTkFrame(pago_frame, fg_color="transparent")
        monto_row.pack(fill="x", padx=4, pady=(2, 0))
        entrada_dinero = ctk.CTkComboBox(
            monto_row,
            variable=entrada_dinero_var,
            values=["", "10000", "20000", "30000", "40000", "50000", "100000"],
            font=tema.FONT_SMALL,
            dropdown_font=tema.FONT_SMALL,
            fg_color=tema.BG_INPUT,
            border_width=0,
            button_color=tema.ACCENT_ORANGE,
            corner_radius=tema.RADIUS_SM,
            height=28,
        )
        entrada_dinero.pack(side="left", fill="x", expand=True, padx=(2, 4))
        entrada_dinero.set(monto_prev)

        def toggle_teclado():
            teclado_visible["on"] = not teclado_visible["on"]
            actualizar_carrito()

        btn_teclado = ctk.CTkButton(
            monto_row,
            text="Teclado ▼" if not teclado_visible["on"] else "Teclado ▲",
            fg_color=tema.ACCENT_BLUE if teclado_visible["on"] else tema.BG_INPUT,
            hover_color=tema.BG_HOVER,
            corner_radius=tema.RADIUS_SM,
            height=28,
            width=88,
            font=tema.FONT_SMALL,
            command=toggle_teclado,
        )
        btn_teclado.pack(side="right", padx=(0, 2))

        ctk.CTkLabel(
            pago_frame,
            textvariable=cambio_var,
            font=tema.FONT_SMALL,
            text_color=tema.ACCENT_GREEN,
        ).pack(anchor="w", padx=10, pady=(1, 2))

        # Teclado: oculto por defecto; aparece al pagar
        if teclado_visible["on"]:
            teclado_frame = ctk.CTkFrame(pago_frame, fg_color=tema.BG_CARD, corner_radius=tema.RADIUS_SM)
            teclado_frame.pack(fill="x", padx=4, pady=(0, 4))

            def agregar_numero(num):
                entrada_dinero.set(entrada_dinero.get() + str(num))

            def borrar():
                entrada_dinero.set(entrada_dinero.get()[:-1])

            botones = [
                ("7", 0, 0), ("8", 0, 1), ("9", 0, 2),
                ("4", 1, 0), ("5", 1, 1), ("6", 1, 2),
                ("1", 2, 0), ("2", 2, 1), ("3", 2, 2),
                ("0", 3, 1), (".", 3, 0), ("←", 3, 2),
            ]
            for texto, fila, col in botones:
                action = borrar if texto == "←" else lambda t=texto: agregar_numero(t)
                ctk.CTkButton(
                    teclado_frame,
                    text=texto,
                    height=tecla_h,
                    font=tema.FONT_BODY_BOLD,
                    fg_color=tema.BG_INPUT,
                    hover_color=tema.BG_HOVER,
                    corner_radius=tema.RADIUS_SM,
                    command=action,
                ).grid(row=fila, column=col, padx=2, pady=2, sticky="ew")
            for c in range(3):
                teclado_frame.grid_columnconfigure(c, weight=1)

        # ===== Acciones fijas (compactas) =====
        styled_button(
            acciones_frame,
            text="🖨  Imprimir factura",
            bg_color=tema.ACCENT_GREEN,
            command=imprimir_factura,
            height=btn_h + 4,
            font=tema.FONT_BTN,
        ).pack(fill="x", pady=(0, 2))

        fila1 = ctk.CTkFrame(acciones_frame, fg_color="transparent")
        fila1.pack(fill="x", pady=1)
        styled_button(
            fila1, text="Eliminar", bg_color=tema.ACCENT_RED, command=eliminar_producto, height=btn_h
        ).pack(side="left", expand=True, fill="x", padx=(0, 2))
        styled_button(
            fila1, text="Nota", bg_color=tema.ACCENT_BLUE, command=editar_nota_producto, height=btn_h
        ).pack(side="left", expand=True, fill="x", padx=(2, 0))

        fila2 = ctk.CTkFrame(acciones_frame, fg_color="transparent")
        fila2.pack(fill="x", pady=1)
        styled_button(
            fila2, text="Pago parcial", bg_color=tema.ACCENT_ORANGE, command=pago_parcial, height=btn_h
        ).pack(side="left", expand=True, fill="x", padx=(0, 2))
        styled_button(
            fila2, text="Fiar", bg_color="#2E7D32", command=fiar_venta_actual, height=btn_h
        ).pack(side="left", expand=True, fill="x", padx=(2, 0))

        fila3 = ctk.CTkFrame(acciones_frame, fg_color="transparent")
        fila3.pack(fill="x", pady=1)
        n_espera = len(listar_facturas_espera(usuario) or [])
        styled_button(
            fila3,
            text="En espera",
            bg_color="#5D4037",
            command=poner_factura_en_espera,
            height=btn_h,
        ).pack(side="left", expand=True, fill="x", padx=(0, 2))
        styled_button(
            fila3,
            text=f"Recuperar ({n_espera})",
            bg_color="#6D4C41",
            command=recuperar_factura_espera,
            height=btn_h,
        ).pack(side="left", expand=True, fill="x", padx=(2, 0))

        fila4 = ctk.CTkFrame(acciones_frame, fg_color="transparent")
        fila4.pack(fill="x", pady=(2, 0))
        styled_button(
            fila4,
            text="Cerrar caja",
            bg_color=tema.ACCENT_RED,
            command=cerrar_caja,
            height=btn_h,
        ).pack(side="left", expand=True, fill="x", padx=(0, 2))
        styled_button(
            fila4,
            text="← Volver",
            bg_color=tema.ACCENT_GRAY,
            command=lambda: [ventana.destroy(), ventana_principal.deiconify()],
            height=btn_h,
        ).pack(side="left", expand=True, fill="x", padx=(2, 0))

    # ===================== LÓGICA DE NEGOCIO =====================
    def agregar_al_carrito(producto):
        # Misma línea solo si mismo producto y misma nota (vacía al agregar)
        for i, item in enumerate(carrito):
            pid, nombre, precio, cant, nota = _item_parts(item)
            if pid == producto[0] and nota == "":
                carrito[i] = (pid, nombre, precio, cant + 1, "")
                break
        else:
            carrito.append((producto[0], producto[1], producto[2], 1, ""))
        actualizar_carrito()

    def editar_nota_producto():
        idx = seleccion_index.get()
        if idx < 0 or idx >= len(carrito):
            messagebox.showinfo("Nota", "Selecciona un producto del pedido primero.")
            return
        pid, nombre, precio, cant, nota_actual = _item_parts(carrito[idx])
        nota = simpledialog.askstring(
            "Nota del producto",
            f"Descripción para «{nombre}»\n(ej: sin salsa, sin queso, bien asada):",
            initialvalue=nota_actual,
            parent=ventana,
        )
        if nota is None:
            return
        carrito[idx] = (pid, nombre, precio, cant, (nota or "").strip()[:80])
        actualizar_carrito()

    def poner_factura_en_espera():
        if not carrito:
            messagebox.showwarning("Vacío", "No hay productos para poner en espera.")
            return
        etiqueta = simpledialog.askstring(
            "Factura en espera",
            "Nombre o mesa del cliente:",
            parent=ventana,
        )
        if not etiqueta or not etiqueta.strip():
            return
        total = float(total_var.get() or 0)
        contenido = json.dumps(
            [
                {
                    "id": _item_parts(it)[0],
                    "nombre": _item_parts(it)[1],
                    "precio": _item_parts(it)[2],
                    "cantidad": _item_parts(it)[3],
                    "nota": _item_parts(it)[4],
                }
                for it in carrito
            ],
            ensure_ascii=False,
        )
        try:
            guardar_factura_espera(usuario, etiqueta.strip()[:60], contenido, total)
            carrito.clear()
            total_var.set(0.0)
            seleccion_index.set(-1)
            actualizar_carrito()
            messagebox.showinfo("En espera", f"Pedido de «{etiqueta.strip()}» guardado.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar en espera:\n{e}")

    def recuperar_factura_espera():
        pendientes = listar_facturas_espera(usuario) or []
        if not pendientes:
            messagebox.showinfo("Recuperar", "No hay facturas en espera.")
            return
        if carrito:
            if not messagebox.askyesno(
                "Pedido actual",
                "Hay productos en el pedido actual.\n¿Reemplazarlos por la factura en espera?",
            ):
                return

        dlg = ctk.CTkToplevel(ventana)
        dlg.title("Facturas en espera")
        dlg.configure(fg_color=tema.BG_APP)
        resp.fit_dialog(dlg, width_ratio=0.36, height_ratio=0.55, min_w=360, min_h=360, max_w=520, max_h=560)
        dlg.grab_set()

        ctk.CTkLabel(
            dlg,
            text="Selecciona un pedido",
            font=tema.FONT_HEADER,
            text_color=tema.TEXT,
        ).pack(pady=(14, 8))

        lista = ctk.CTkScrollableFrame(dlg, fg_color=tema.BG_PANEL, corner_radius=tema.RADIUS)
        lista.pack(fill="both", expand=True, padx=14, pady=8)

        def cargar(fid):
            fila = obtener_factura_espera(fid)
            if not fila:
                messagebox.showerror("Error", "La factura ya no existe.")
                dlg.destroy()
                return
            try:
                items = json.loads(fila["contenido"])
            except Exception:
                messagebox.showerror("Error", "Datos de espera corruptos.")
                return
            carrito.clear()
            for it in items:
                carrito.append(
                    (
                        it.get("id"),
                        it.get("nombre"),
                        float(it.get("precio") or 0),
                        int(it.get("cantidad") or 1),
                        (it.get("nota") or "").strip(),
                    )
                )
            eliminar_factura_espera(fid)
            seleccion_index.set(-1)
            actualizar_carrito()
            dlg.destroy()

        def borrar(fid):
            if messagebox.askyesno("Eliminar", "¿Eliminar esta factura en espera?"):
                eliminar_factura_espera(fid)
                dlg.destroy()
                recuperar_factura_espera()

        for row in pendientes:
            card = ctk.CTkFrame(lista, fg_color=tema.BG_CARD, corner_radius=tema.RADIUS_SM)
            card.pack(fill="x", pady=4, padx=4)
            ctk.CTkLabel(
                card,
                text=f"{row['etiqueta']}  ·  ${float(row['total'] or 0):,.0f}",
                font=tema.FONT_BODY_BOLD,
                text_color=tema.TEXT,
                anchor="w",
            ).pack(fill="x", padx=10, pady=(8, 0))
            ctk.CTkLabel(
                card,
                text=str(row["creado"]),
                font=tema.FONT_SMALL,
                text_color=tema.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x", padx=10, pady=(0, 6))
            btns = ctk.CTkFrame(card, fg_color="transparent")
            btns.pack(fill="x", padx=8, pady=(0, 8))
            ctk.CTkButton(
                btns,
                text="Recuperar",
                fg_color=tema.ACCENT_GREEN,
                height=32,
                command=lambda i=row["id"]: cargar(i),
            ).pack(side="left", expand=True, fill="x", padx=(0, 4))
            ctk.CTkButton(
                btns,
                text="Borrar",
                fg_color=tema.ACCENT_RED,
                height=32,
                command=lambda i=row["id"]: borrar(i),
            ).pack(side="left", expand=True, fill="x", padx=(4, 0))

    def registrar_venta_parcial(pagos):
        try:
            fecha = fh.datetime_sql()
            fila_caja = obtener_caja_abierta(usuario)
            if not fila_caja:
                messagebox.showerror("Error", "No hay caja abierta.")
                return
            id_caja = fila_caja["id"]

            conn = get_connection()
            cur = conn.cursor()
            for i, producto in enumerate(carrito):
                producto_id, nombre, precio_unitario, cantidad_vendida, nota = _item_parts(producto)
                total_producto = precio_unitario * cantidad_vendida
                # El desglose de métodos solo en la 1ª línea (evita sumar N veces en reportes)
                metodo = f"Pago parcial: {pagos}" if i == 0 else "Pago parcial"

                cur.execute("UPDATE productos SET stock = stock - ? WHERE id = ?", (cantidad_vendida, producto_id))
                try:
                    cur.execute(
                        """
                        INSERT INTO ventas (
                            fecha, producto_id, nombre_producto, cantidad, precio_unitario,
                            total, metodo_pago, id_caja, nota
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            fecha,
                            producto_id,
                            nombre,
                            cantidad_vendida,
                            precio_unitario,
                            total_producto,
                            metodo,
                            id_caja,
                            nota or None,
                        ),
                    )
                except Exception:
                    cur.execute(
                        """
                        INSERT INTO ventas (
                            fecha, producto_id, nombre_producto, cantidad, precio_unitario,
                            total, metodo_pago, id_caja
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            fecha,
                            producto_id,
                            nombre,
                            cantidad_vendida,
                            precio_unitario,
                            total_producto,
                            metodo,
                            id_caja,
                        ),
                    )

            conn.commit()
            conn.close()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def pago_parcial():
        if not carrito:
            messagebox.showwarning("Vacío", "No hay productos en el carrito")
            return

        ventana_pago = ctk.CTkToplevel(ventana)
        ventana_pago.title("Pago parcial")
        ventana_pago.configure(fg_color=tema.BG_APP)
        resp.fit_dialog(ventana_pago, width_ratio=0.30, height_ratio=0.48, min_w=320, min_h=320, max_w=440, max_h=480)
        ventana_pago.grab_set()

        metodos = ["Efectivo", "Tarjeta", "Nequi", "Transferencia"]
        entradas = {}
        total_factura = total_var.get()
        total_parcial_var = tk.DoubleVar(value=0.0)

        def actualizar_total():
            total = 0
            for m in metodos:
                try:
                    val = float(entradas[m].get())
                except ValueError:
                    val = 0
                total += val
            total_parcial_var.set(total)

        ctk.CTkLabel(
            ventana_pago,
            text=f"Total factura: ${total_factura:,.2f}",
            font=tema.FONT_HEADER,
            text_color=tema.TEXT,
        ).pack(pady=12)

        for m in metodos:
            frame = ctk.CTkFrame(ventana_pago, fg_color="transparent")
            frame.pack(fill="x", padx=16, pady=4)
            ctk.CTkLabel(frame, text=m, width=110, anchor="w", font=tema.FONT_BODY).pack(side="left")
            e = ctk.CTkEntry(frame, width=160, corner_radius=tema.RADIUS_SM, fg_color=tema.BG_INPUT, border_width=0)
            e.pack(side="right")
            e.insert(0, "0")
            e.bind("<KeyRelease>", lambda e: actualizar_total())
            entradas[m] = e

        ctk.CTkLabel(
            ventana_pago,
            textvariable=total_parcial_var,
            font=tema.FONT_BODY_BOLD,
            text_color=tema.ACCENT_ORANGE,
        ).pack(pady=10)

        def confirmar():
            if abs(total_parcial_var.get() - total_factura) > 0.01:
                messagebox.showerror("Error", "Los montos no coinciden con el total de la factura.")
                return
            pagos = {m: float(entradas[m].get()) for m in metodos if float(entradas[m].get()) > 0}
            imprimir_ticket_real(carrito, total_factura, "Pago parcial", pagos, 0)
            registrar_venta_parcial(pagos)
            carrito.clear()
            total_var.set(0.0)
            actualizar_carrito()
            ventana_pago.destroy()

        ctk.CTkButton(
            ventana_pago,
            text="Confirmar",
            fg_color=tema.ACCENT_GREEN,
            corner_radius=tema.RADIUS_BTN,
            height=42,
            font=tema.FONT_BTN,
            command=confirmar,
        ).pack(pady=14)

    def imprimir_factura():
        if not carrito:
            messagebox.showwarning("Vacío", "No hay productos en el carrito")
            return
        try:
            total = total_var.get()
            Dinero_recibido = float(entrada_dinero.get())
            cambio = Dinero_recibido - total
            imprimir_ticket_real(carrito, total, metodo_pago.get(), Dinero_recibido, cambio)
            registrar_venta()
            carrito.clear()
            total_var.set(0.0)
            actualizar_carrito()
        except ValueError:
            messagebox.showerror("Error", "Monto recibido inválido")

    def fiar_venta_actual():
        if not carrito:
            messagebox.showwarning("Carrito vacío", "No hay productos en el carrito para fiar.")
            return
        nombre_cliente = simpledialog.askstring("Fiar Venta", "Ingrese el nombre del cliente:")
        if not nombre_cliente:
            return

        total = total_var.get()

        # Registrar como Fiado (no con el método de la combo)
        metodo_anterior = metodo_pago.get() if metodo_pago else "Efectivo"
        try:
            metodo_pago.set("Fiado")
        except Exception:
            pass
        registrar_venta()
        try:
            metodo_pago.set(metodo_anterior)
        except Exception:
            pass

        # Registrar el fiado
        try:
            registrar_fiado(nombre_cliente, total)
            messagebox.showinfo("Fiado registrado", f"Se ha fiado ${total:,.2f} a {nombre_cliente}.")
        except Exception as e:
            messagebox.showerror("Error al registrar fiado", str(e))

        # Imprimir factura (si quieres que imprima)
        imprimir_ticket_real(carrito, total, "Fiado", total, 0)

        # Limpiar carrito y actualizar
        carrito.clear()
        total_var.set(0.0)
        actualizar_carrito()

    def registrar_venta():
        try:
            fecha = fh.datetime_sql()
            metodo = metodo_pago.get()

            fila_caja = obtener_caja_abierta(usuario)
            if not fila_caja:
                messagebox.showerror("Error", "No hay caja abierta. Debes hacer apertura antes de vender.")
                return
            id_caja = fila_caja["id"]

            conn = get_connection()
            cur = conn.cursor()
            try:
                for producto in carrito:
                    producto_id, nombre, precio_unitario, cantidad_vendida, nota = _item_parts(producto)
                    total_producto = precio_unitario * cantidad_vendida

                    cur.execute("SELECT stock FROM productos WHERE id = ?", (producto_id,))
                    row = cur.fetchone()
                    if not row or cantidad_vendida > row["stock"]:
                        raise ValueError(
                            f"No hay suficiente stock de {nombre}. Disponible: {row['stock'] if row else 0}"
                        )

                    cur.execute(
                        "UPDATE productos SET stock = stock - ? WHERE id = ?",
                        (cantidad_vendida, producto_id),
                    )

                    try:
                        cur.execute(
                            """
                            INSERT INTO ventas (
                                fecha, producto_id, nombre_producto, cantidad, precio_unitario,
                                total, metodo_pago, id_caja, nota
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                fecha,
                                producto_id,
                                nombre,
                                cantidad_vendida,
                                precio_unitario,
                                total_producto,
                                metodo,
                                id_caja,
                                nota or None,
                            ),
                        )
                    except Exception:
                        cur.execute(
                            """
                            INSERT INTO ventas (
                                fecha, producto_id, nombre_producto, cantidad, precio_unitario,
                                total, metodo_pago, id_caja
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                fecha,
                                producto_id,
                                nombre,
                                cantidad_vendida,
                                precio_unitario,
                                total_producto,
                                metodo,
                                id_caja,
                            ),
                        )

                conn.commit()
            except Exception as e:
                conn.rollback()
                messagebox.showerror("Error al registrar venta", str(e))
            finally:
                conn.close()

        except Exception as e_outer:
            messagebox.showerror("Error", str(e_outer))

    def cargar_productos(categoria):
        _resaltar_categoria(categoria)
        for widget in productos_frame.winfo_children():
            widget.destroy()

        productos = consultar_todos(
            "SELECT id, nombre, precio, stock, stock_inicial FROM productos WHERE categoria = ?",
            (categoria,),
        )

        filtro = (search_var.get() or "").strip().lower()
        if filtro:
            productos = [r for r in productos if filtro in str(r["nombre"]).lower()]

        try:
            productos_frame.update_idletasks()
            ancho = productos_frame.winfo_width()
        except Exception:
            ancho = 700
        columnas = resp.product_columns_for_width(max(ancho, 400))
        layout_cols["n"] = columnas
        for index, row in enumerate(productos):
            prod_id = row["id"]
            nombre = row["nombre"]
            precio = row["precio"]
            stock = row["stock"]
            stock_inicial = row["stock_inicial"]

            card = ctk.CTkFrame(
                productos_frame,
                fg_color=tema.BG_CARD,
                corner_radius=tema.RADIUS,
                border_width=0,
            )
            card.grid(row=index // columnas, column=index % columnas, padx=8, pady=8, sticky="nsew")
            productos_frame.grid_columnconfigure(index % columnas, weight=1)

            # Cabecera visual (placeholder de imagen)
            banner = ctk.CTkFrame(card, fg_color=tema.BG_INPUT, corner_radius=tema.RADIUS_SM, height=72)
            banner.pack(fill="x", padx=10, pady=(10, 6))
            banner.pack_propagate(False)
            ctk.CTkLabel(
                banner,
                text=nombre[:1].upper(),
                font=(tema.FONT_FAMILY, 28, "bold"),
                text_color=tema.ACCENT_ORANGE,
            ).place(relx=0.5, rely=0.5, anchor="center")

            ctk.CTkLabel(
                card,
                text=nombre.upper(),
                font=tema.FONT_BODY_BOLD,
                text_color=tema.TEXT,
                wraplength=160,
            ).pack(padx=10, pady=(0, 2))

            ctk.CTkLabel(
                card,
                text=f"Stock: {stock}/{stock_inicial}",
                font=tema.FONT_SMALL,
                text_color=tema.TEXT_MUTED,
            ).pack(padx=10)

            footer = ctk.CTkFrame(card, fg_color=tema.BG_INPUT, corner_radius=tema.RADIUS_SM, height=40)
            footer.pack(fill="x", padx=10, pady=10)
            footer.pack_propagate(False)

            ctk.CTkLabel(
                footer,
                text=f"${precio:,.0f}",
                font=tema.FONT_BODY_BOLD,
                text_color=tema.TEXT,
            ).pack(side="left", padx=12)

            ctk.CTkButton(
                footer,
                text="+ Agregar",
                width=100,
                height=30,
                fg_color=tema.ACCENT_ORANGE,
                hover_color="#E67E00",
                corner_radius=tema.RADIUS_SM,
                font=tema.FONT_SMALL,
                command=lambda p=(prod_id, nombre, precio): agregar_al_carrito(p),
            ).pack(side="right", padx=8)

    def on_search(*_args):
        if categoria_activa["nombre"]:
            cargar_productos(categoria_activa["nombre"])

    search_var.trace_add("write", on_search)

    # --- Aquí se crea UNA vez la lista de categorías y los botones (solo 1 bloque) ---
    categorias_rows = consultar_todos("SELECT DISTINCT categoria FROM productos")
    categorias = [row[0] for row in categorias_rows]

    for i, cat in enumerate(categorias):
        color = tema.CATEGORY_COLORS[i % len(tema.CATEGORY_COLORS)]
        btn = ctk.CTkButton(
            frame_categorias,
            text=cat.upper(),
            fg_color=color,
            hover_color=tema.BG_HOVER,
            text_color="#111111",
            corner_radius=tema.RADIUS,
            height=64,
            font=tema.FONT_BTN,
            command=lambda c=cat: cargar_productos(c),
        )
        btn.pack(fill="x", padx=8, pady=6)
        botones_categoria[cat] = btn

    if categorias:
        cargar_productos(categorias[0])

    denominaciones = [
        ("Billetes de $100.000", 100000),
        ("Billetes de $50.000", 50000),
        ("Billetes de $20.000", 20000),
        ("Billetes de $10.000", 10000),
        ("Billetes de $5.000", 5000),
        ("Billetes de $2.000", 2000),
        ("Monedas de $1.000", 1000),
        ("Monedas de $500", 500),
        ("Monedas de $200", 200),
        ("Monedas de $100", 100),
        ("Monedas de $50", 50),
    ]

    class CashCountWindow(ctk.CTkToplevel):
        def __init__(self, master, mode="apertura", expected_total=0, callback=None):
            super().__init__(master)
            self.title("Apertura de Caja" if mode == "apertura" else "Cierre de Caja")
            self.configure(fg_color=tema.BG_APP)
            self.mode = mode
            self.expected_total = expected_total
            self.callback = callback
            self.entries = {}
            self.total_var = tk.StringVar(value="$0")
            resp.fit(
                self,
                width_ratio=0.34,
                height_ratio=0.88,
                min_w=360,
                min_h=520,
                max_w=520,
                max_h=900,
                resizable=True,
            )
            self._build_ui()
            self._update_total()
            self.grab_set()
            self.update_idletasks()

        def _build_ui(self):
            header_text = "Apertura de Caja" if self.mode == "apertura" else "Cierre de Caja"
            header = ctk.CTkLabel(self, text=header_text, font=tema.FONT_TITLE, text_color=tema.TEXT)
            header.grid(row=0, column=0, columnspan=3, pady=(14, 16), sticky="ew", padx=12)

            self.columnconfigure(0, weight=0)
            self.columnconfigure(1, weight=0)

            for i, (label_text, value) in enumerate(denominaciones, start=1):
                lbl = ctk.CTkLabel(self, text=label_text, anchor="w", font=tema.FONT_BODY, text_color=tema.TEXT)
                lbl.grid(row=i, column=0, sticky="w", padx=12, pady=3)
                ent = ctk.CTkEntry(
                    self,
                    width=90,
                    corner_radius=tema.RADIUS_SM,
                    fg_color=tema.BG_INPUT,
                    border_width=0,
                )
                ent.grid(row=i, column=1, padx=8)
                ent.insert(0, "0")
                ent.bind("<KeyRelease>", lambda e: self._update_total())
                self.entries[value] = ent

            total_lbl = ctk.CTkLabel(self, text="Total:", font=tema.FONT_BODY_BOLD)
            total_lbl.grid(row=len(denominaciones) + 1, column=0, pady=(12, 6), sticky="e", padx=12)
            total_val = ctk.CTkLabel(
                self,
                textvariable=self.total_var,
                font=tema.FONT_BODY_BOLD,
                text_color=tema.ACCENT_GREEN,
                width=120,
                anchor="w",
            )
            total_val.grid(row=len(denominaciones) + 1, column=1, pady=(12, 6), sticky="w")

            btn_frame = ctk.CTkFrame(self, fg_color="transparent")
            btn_frame.grid(row=len(denominaciones) + 2, column=0, columnspan=2, pady=14)

            save_text = "Guardar y Continuar" if self.mode == "apertura" else "Cerrar Caja"
            ctk.CTkButton(
                btn_frame,
                text=save_text,
                width=200,
                height=40,
                fg_color=tema.ACCENT_GREEN,
                corner_radius=tema.RADIUS_BTN,
                command=self._on_save,
            ).pack(pady=4)
            ctk.CTkButton(
                btn_frame,
                text="← Volver",
                width=200,
                height=36,
                fg_color=tema.ACCENT_GRAY,
                corner_radius=tema.RADIUS_BTN,
                command=self.destroy,
            ).pack(pady=4)

        def _update_total(self):
            total = 0
            for denom_value, entry in self.entries.items():
                try:
                    qty = int(entry.get())
                    if qty < 0:
                        qty = 0
                    total += denom_value * qty
                except ValueError:
                    continue
            self.current_total = total
            self.total_var.set(f"${total:,.2f}")

        def _on_save(self):
            if self.mode == "cierre":
                diff = self.current_total - self.expected_total
                if diff != 0:
                    resp = messagebox.askyesno(
                        "Diferencia detectada",
                        f"El total contado ({self.total_var.get()}) difiere del esperado "
                        f"${self.expected_total:,.2f}.\n¿Deseas continuar?",
                    )
                    if not resp:
                        return
            if self.callback:
                self.callback(self.current_total)
            self.destroy()

    def cerrar_caja():
        fila = obtener_caja_abierta(usuario)
        if not fila:
            messagebox.showerror("Error", "No se encontró una caja abierta.")
            return

        id_caja = fila["id"]
        capital_inicial = float(fila["capital_inicial"] or 0)
        fecha_apertura = fila["fecha"]
        hora_apertura = fila["hora_apertura"]

        total_ventas_row = consultar_uno(
            "SELECT SUM(total) as suma FROM ventas WHERE id_caja = ?",
            (id_caja,),
        )
        total_ventas = float(total_ventas_row["suma"] or 0.0)

        # Esperado en cajón = capital + solo efectivo del turno (no tarjeta/Nequi/etc.)
        conn = get_connection()
        try:
            efectivo_turno = float(efectivo_del_turno(conn.cursor(), id_caja))
        finally:
            conn.close()
        capital_esperado = capital_inicial + efectivo_turno

        def al_cerrar(capital_final):
            diferencia = capital_final - capital_esperado
            ahora = fh.ahora()
            fecha_cierre = fh.fecha_sql(ahora)
            hora_cierre = fh.hora_sql(ahora)
            resumen = (
                f"Resumen de cierre de caja:\n\n"
                f"Apertura: {fecha_apertura} {hora_apertura}\n"
                f"Cierre:   {fecha_cierre} {hora_cierre}\n\n"
                f"Capital inicial: ${capital_inicial:,.2f}\n"
                f"Total ventas (todos los medios): ${total_ventas:,.2f}\n"
                f"Efectivo del turno: ${efectivo_turno:,.2f}\n"
                f"Esperado en caja (inicial + efectivo): ${capital_esperado:,.2f}\n"
                f"Capital final contado: ${capital_final:,.2f}\n"
                f"{'Sobrante' if diferencia > 0 else 'Faltante'}: ${abs(diferencia):,.2f}"
            )
            if not messagebox.askyesno("Confirmar cierre", resumen + "\n\n¿Confirmar cierre de caja?"):
                return

            try:
                ejecutar(
                    """
                    UPDATE caja
                    SET hora_cierre = ?, fecha_cierre = ?, capital_final = ?, total_ventas = ?
                    WHERE id = ?
                    """,
                    (hora_cierre, fecha_cierre, capital_final, total_ventas, id_caja),
                )
            except Exception:
                ejecutar(
                    """
                    UPDATE caja
                    SET hora_cierre = ?, capital_final = ?, total_ventas = ?
                    WHERE id = ?
                    """,
                    (hora_cierre, capital_final, total_ventas, id_caja),
                )

            try:
                texto = armar_texto_reporte_diario(usuario, id_caja=id_caja)
                imprimir_texto(texto)
            except Exception as e:
                messagebox.showwarning(
                    "Impresión",
                    f"Caja cerrada, pero no se pudo imprimir el reporte:\n{e}",
                )

            messagebox.showinfo(
                "Turno cerrado",
                f"Caja cerrada correctamente.\n"
                f"Apertura: {fecha_apertura} {hora_apertura}\n"
                f"Cierre: {fecha_cierre} {hora_cierre}\n\n"
                f"Se cerrará la sesión.",
            )

            try:
                mostrar_despedida(usuario, parent=ventana)
            except Exception:
                pass

            # Salir de caja y cerrar sesión → login
            try:
                ventana.destroy()
            except Exception:
                pass
            if ventana_principal:
                try:
                    ventana_principal.destroy()
                except Exception:
                    pass
            from ventana_login import iniciar_login

            iniciar_login()

        CashCountWindow(ventana, mode="cierre", expected_total=capital_esperado, callback=al_cerrar)

    # Mostrar carrito vacío desde el inicio
    actualizar_carrito()

    # Entrada visual (no afecta ventas)
    cat_btns = list(botones_categoria.values())
    anim.soft_entrance(
        ventana,
        title=header_title,
        panels=[frame_categorias, productos_panel, panel_carrito],
        buttons=cat_btns[:4],
        accent=tema.ACCENT_ORANGE,
    )

    def on_caja_resize(_event):
        # Recalcular columnas del grid de productos al cambiar el tamaño
        try:
            productos_frame.update_idletasks()
            ancho = productos_frame.winfo_width()
        except Exception:
            return
        nuevas = resp.product_columns_for_width(max(ancho, 400))
        if nuevas != layout_cols["n"] and categoria_activa["nombre"]:
            layout_cols["n"] = nuevas
            cargar_productos(categoria_activa["nombre"])

        # Ajustar anchos laterales mínimos según ventana actual
        mw = resp.metrics(ventana)
        body.grid_columnconfigure(0, minsize=mw["sidebar"])
        body.grid_columnconfigure(2, minsize=mw["cart"])
        try:
            search_entry.configure(width=mw["search_w"])
            panel_carrito.configure(width=mw["cart"])
        except Exception:
            pass

    resp.bind_resize(ventana, on_caja_resize, delay_ms=140)

    ventana.mainloop()
