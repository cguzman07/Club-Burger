import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from impresion import imprimir_ticket_real
from reportes_impresion import armar_texto_reporte_diario, imprimir_texto
from database import get_connection, ejecutar, consultar_uno, consultar_todos


def ventana_caja(usuario, ventana_principal):
    if ventana_principal:
        ventana_principal.withdraw()

    ventana = tk.Toplevel()
    ventana.title("Caja - Punto de Venta")
    ventana.geometry("1000x700")
    ventana.configure(bg="#d7f1d9")

    BASE_FONT = ("Segoe UI", 13)
    TITLE_FONT = ("Segoe UI", 24, "bold")

    header_frame = tk.Frame(ventana, bg="#d7f1d9", pady=10)
    header_frame.pack(fill="x")
    tk.Label(header_frame, text="Caja - Punto de Venta", font=TITLE_FONT, bg="#d7f1d9").pack(side="left", padx=20)
    tk.Label(header_frame, text=f"Usuario: {usuario}", font=BASE_FONT, fg="#555", bg="#d7f1d9").pack(side="right", padx=20)

    def styled_button(parent, text, bg_color, fg="white", command=None, width=None, height=None):
        btn = tk.Button(parent, text=text, bg=bg_color, fg=fg, relief="flat", command=command,
                        cursor="hand2", font=BASE_FONT)
        if width: btn.config(width=width)
        if height: btn.config(height=height)
        def on_enter(e): btn.config(bg=_adjust_color(bg_color, -0.08))
        def on_leave(e): btn.config(bg=bg_color)
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        return btn

    def _adjust_color(hex_color, factor=0):
        hex_color = hex_color.lstrip("#")
        r, g, b = [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]
        clamp = lambda v: max(0, min(255, int(v * (1 + factor))))
        return f"#{clamp(r):02x}{clamp(g):02x}{clamp(b):02x}"

    frame_categorias = tk.Frame(ventana, bg="#bef3d2")
    frame_categorias.pack(side="left", fill="y", padx=10, pady=10)

    productos_frame_container = tk.Frame(ventana, bg="#bef3d2")
    productos_frame_container.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)

    # --- Scroll de productos ---
    canvas = tk.Canvas(productos_frame_container, bg="#d7f1d9", highlightthickness=0)
    scrollbar = tk.Scrollbar(productos_frame_container, orient="vertical", command=canvas.yview)
    productos_frame = tk.Frame(canvas, bg="#d7f1d9")

    productos_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=productos_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Scroll con rueda del ratón
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # Windows y Mac
    canvas.bind_all("<MouseWheel>", _on_mousewheel)
    # Linux
    canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
    canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))
    # --- Fin Scroll de productos ---

    frame_carrito = tk.Frame(ventana, bg="#cdf5d0", width=250)
    frame_carrito.pack(side="right", fill="y", padx=(0,10), pady=10)

    carrito = []
    total_var = tk.DoubleVar(value=0.0)

    def agregar_al_carrito(producto):
        for i, item in enumerate(carrito):
            if item[0] == producto[0]:
                carrito[i] = (item[0], item[1], item[2], item[3] + 1)
                break
        else:
            carrito.append((producto[0], producto[1], producto[2], 1))
        actualizar_carrito()
        
        
    seleccion_index = tk.IntVar(value=-1)
    def actualizar_carrito():
        global metodo_pago, entrada_dinero

        for widget in frame_carrito.winfo_children():
            widget.destroy()

        labels_items = []  # Guardará referencias a cada label 

        def seleccionar_item(idx):
            seleccion_index.set(idx)
            # Restaurar todos al color original
            for lbl in labels_items:
                lbl.config(bg="#cdf5d0")
            if 0 <= idx < len(labels_items):
                labels_items[idx].config(bg="#8ff186")  # Verde suave

        def eliminar_producto():
            idx = seleccion_index.get()
            if idx != -1 and idx < len(carrito):
                carrito.pop(idx)
                seleccion_index.set(-1)
                actualizar_carrito()

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

        tk.Label(frame_carrito, text="Carrito", bg="#cdf5d0", font=("Arial", 14, "bold")).pack(pady=5)
        total = 0
        for idx, item in enumerate(carrito):
            producto_id, nombre, precio, cantidad = item
            lbl = tk.Label(
                frame_carrito, 
                text=f"{nombre} x{cantidad} - ${precio * cantidad:,.2f}",
                bg="#cdf5d0",
                font=("Segoe UI", 10),
                anchor="w"
            )
            
            lbl.pack(fill="x", padx=10)
            lbl.bind("<Button-1>", lambda e, i=idx: seleccionar_item(i))
            labels_items.append(lbl)  # Guardar referencia
            total += precio * cantidad

        total_var.set(total)
        tk.Label(frame_carrito, text=f"Total: ${total:,.2f}", bg="#cdf5d0", font=("Segoe UI", 12, "bold")).pack(pady=(5,10))
        tk.Label(frame_carrito, text="Método de pago:", bg="#cdf5d0").pack(padx=10, anchor="w")
        metodo_pago = ttk.Combobox(frame_carrito, values=["Efectivo", "Tarjeta", "Nequi", "Transferencia"], font=BASE_FONT)
        metodo_pago.pack(padx=10, fill="x")
        metodo_pago.current(0)

        entrada_dinero_var = tk.StringVar()
        cambio_var = tk.StringVar(value="Cambio: $0.00")

        def calcular_cambio(*args):
            try:
                recibido = float(entrada_dinero_var.get())
                cambio = recibido - total_var.get()
                cambio_var.set(f"Cambio: ${cambio:,.2f}")
            except ValueError:
                cambio_var.set("Monto inválido")

        entrada_dinero_var.trace_add("write", calcular_cambio)

        entrada_dinero = ttk.Combobox(
            frame_carrito,
            textvariable=entrada_dinero_var,
            values=["","10000", "20000", "50000", "100000"],
            font=BASE_FONT
        )
        entrada_dinero.pack(padx=10, fill="x")
        entrada_dinero.current(0)

        tk.Label(frame_carrito, textvariable=cambio_var, bg="#cdf5d0", fg="black", font=BASE_FONT).pack(pady=(5,0))
    
        # Botón eliminar producto
        styled_button(frame_carrito, text="Eliminar producto", bg_color="#E53935", command=eliminar_producto).pack(padx=10, fill="x", pady=5)

        # Botón imprimir
        styled_button(frame_carrito, text="Imprimir factura", bg_color="#4CAF50", command=imprimir_factura).pack(padx=10, fill="x", pady=5)

        # ======= TECLADO NUMÉRICO =======
        teclado_frame = tk.Frame(frame_carrito, bg="#cdf5d0")
        teclado_frame.pack(pady=5)

        def agregar_numero(num):
            entrada_dinero.set(entrada_dinero.get() + str(num))

        def borrar():
            entrada_dinero.set(entrada_dinero.get()[:-1])

        botones = [
            ('7', 0, 0), ('8', 0, 1), ('9', 0, 2),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2),
            ('1', 2, 0), ('2', 2, 1), ('3', 2, 2),
            ('0', 3, 1), ('.', 3, 0), ('←', 3, 2)
        ]

        for (texto, fila, col) in botones:
            action = borrar if texto == '←' else lambda t=texto: agregar_numero(t)
            tk.Button(teclado_frame, text=texto, width=4, height=2, font=BASE_FONT,
                      command=action, bg="#e0e0e0").grid(row=fila, column=col, padx=2, pady=2)

    def registrar_venta():
        try:
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            metodo = metodo_pago.get()

            fila_caja = consultar_uno(
                "SELECT id, capital_inicial FROM caja WHERE fecha = ? AND usuario = ? AND hora_cierre IS NULL ORDER BY id DESC LIMIT 1",
                (datetime.now().strftime("%Y-%m-%d"), usuario)
            )
            if not fila_caja:
                messagebox.showerror("Error", "No hay caja abierta. Debes hacer apertura antes de vender.")
                return
            id_caja = fila_caja["id"]

            conn = get_connection()
            cur = conn.cursor()
            try:
                for producto in carrito:
                    producto_id, nombre, precio_unitario, cantidad_vendida = producto
                    total_producto = precio_unitario * cantidad_vendida

                    cur.execute("SELECT stock FROM productos WHERE id = ?", (producto_id,))
                    row = cur.fetchone()
                    if not row or cantidad_vendida > row["stock"]:
                        raise ValueError(f"No hay suficiente stock de {nombre}. Disponible: {row['stock'] if row else 0}")

                    cur.execute("UPDATE productos SET stock = stock - ? WHERE id = ?", (cantidad_vendida, producto_id))

                    cur.execute("""
                        INSERT INTO ventas (
                            fecha, producto_id, nombre_producto, cantidad, precio_unitario, total, metodo_pago, id_caja
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (fecha, producto_id, nombre, cantidad_vendida, precio_unitario, total_producto, metodo, id_caja))

                conn.commit()
            except Exception as e:
                conn.rollback()
                messagebox.showerror("Error al registrar venta", str(e))
            finally:
                conn.close()

        except Exception as e_outer:
            messagebox.showerror("Error", str(e_outer))

    def cargar_productos(categoria):
        for widget in productos_frame.winfo_children():
            widget.destroy()

        productos = consultar_todos(
            "SELECT id, nombre, precio, stock, stock_inicial FROM productos WHERE categoria = ?",
            (categoria,)
        )

        columnas = 3
        for index, row in enumerate(productos):
            prod_id = row["id"]
            nombre = row["nombre"]
            precio = row["precio"]
            stock = row["stock"]
            stock_inicial = row["stock_inicial"]

            frame = tk.Frame(productos_frame, bd=1, relief="solid", bg="#d7f1d9", padx=10, pady=5)
            frame.grid(row=index // columnas, column=index % columnas, padx=10, pady=10, sticky="nsew")

            lbl_nombre = tk.Label(frame, text=nombre, font=("Segoe UI", 12, "bold"), bg="#d7f1d9")
            lbl_nombre.pack()
            lbl_precio = tk.Label(frame, text=f"${precio:,.0f}", font=("Segoe UI", 10), bg="#d7f1d9")
            lbl_precio.pack()
            lbl_stock = tk.Label(frame, text=f"Stock: {stock}/{stock_inicial}", font=("Segoe UI", 9), bg="#d7f1d9", fg="gray")
            lbl_stock.pack()

            btn_agregar = tk.Button(frame, text="Agregar", bg="#2196F3", fg="white",
                                    command=lambda p=(prod_id, nombre, precio): agregar_al_carrito(p))
            btn_agregar.pack(pady=5)

    categorias_rows = consultar_todos("SELECT DISTINCT categoria FROM productos")
    categorias = [row[0] for row in categorias_rows]

    for cat in categorias:
        btn = styled_button(
            frame_categorias,
            text=cat,
            bg_color="#1976D2",
            command=lambda c=cat: cargar_productos(c),
            width=18,
            height=2
        )
        btn.pack(padx=5, pady=5)

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

    class CashCountWindow(tk.Toplevel):
        def __init__(self, master, mode="apertura", expected_total=0, callback=None):
            super().__init__(master)
            self.title("Apertura de Caja" if mode == "apertura" else "Cierre de Caja")
            self.mode = mode
            self.expected_total = expected_total
            self.callback = callback
            self.entries = {}
            self.total_var = tk.StringVar(value="$0")
            self._build_ui()
            self._update_total()
            self.grab_set()
            self.update_idletasks()
            self.minsize(self.winfo_width(), self.winfo_height())
            self.resizable(False, False)

        def _build_ui(self):
            header_text = "Apertura de Caja" if self.mode == "apertura" else "Cierre de Caja"
            header = tk.Label(self, text=header_text, font=("Segoe UI", 16, "bold"))
            header.grid(row=0, column=0, columnspan=3, pady=(10, 15), sticky="ew")
            
            # Evitar repropagación extraña y fijar columnas
            self.columnconfigure(0, weight=0)
            self.columnconfigure(1, weight=0)

            for i, (label_text, value) in enumerate(denominaciones, start=1):
                lbl = tk.Label(self, text=label_text, anchor="w")
                lbl.grid(row=i, column=0, sticky="w", padx=10, pady=2)
                ent = tk.Entry(self, width=10)
                ent.grid(row=i, column=1, padx=5)
                ent.insert(0, "0")
                ent.bind("<KeyRelease>", lambda e: self._update_total())
                self.entries[value] = ent

            total_lbl = tk.Label(self, text="Total:", font=("Segoe UI", 12))
            total_lbl.grid(row=len(denominaciones)+1, column=0, pady=(10, 5), sticky="e")
            total_val = tk.Label(self, textvariable=self.total_var, font=("Segoe UI", 12, "bold"),
                                width=14, anchor="w")
            total_val.grid(row=len(denominaciones)+1, column=1, pady=(10, 5), sticky="w")

            btn_frame = tk.Frame(self)
            btn_frame.grid(row=len(denominaciones)+2, column=0, columnspan=2, pady=10)

            save_text = "Guardar y Continuar" if self.mode == "apertura" else "Cerrar Caja"
            save_btn = tk.Button(btn_frame, text=save_text, width=20, command=self._on_save)
            save_btn.pack(pady=3)
            back_btn = tk.Button(btn_frame, text="← Volver", width=20, command=self.destroy)
            back_btn.pack(pady=3)

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
                        f"${self.expected_total:,.2f}.\n¿Deseas continuar?"
                    )
                    if not resp:
                        return
            if self.callback:
                self.callback(self.current_total)
            self.destroy()
            
    def cerrar_caja():
        hoy = datetime.now().strftime("%Y-%m-%d")
        fila = consultar_uno(
            """
            SELECT id, capital_inicial
            FROM caja
            WHERE fecha = ? AND usuario = ? AND hora_cierre IS NULL
            ORDER BY id DESC
            LIMIT 1
            """,
            (hoy, usuario)
        )
        if not fila:
            messagebox.showerror("Error", "No se encontró una caja abierta para hoy.")
            return

        id_caja = fila["id"]
        capital_inicial = fila["capital_inicial"]

        total_ventas_row = consultar_uno("SELECT SUM(total) as suma FROM ventas WHERE id_caja = ?", (id_caja,))
        total_ventas = total_ventas_row["suma"] or 0.0
        capital_esperado = capital_inicial + total_ventas

        def al_cerrar(capital_final):
            diferencia = capital_final - capital_esperado
            resumen = (
                f"Resumen de cierre de caja:\n\n"
                f"Capital inicial: ${capital_inicial:,.2f}\n"
                f"Total ventas: ${total_ventas:,.2f}\n"
                f"Capital esperado: ${capital_esperado:,.2f}\n"
                f"Capital final contado: ${capital_final:,.2f}\n"
                f"{'Sobrante' if diferencia > 0 else 'Faltante'}: ${abs(diferencia):,.2f}"
            )
            if not messagebox.askyesno("Confirmar cierre", resumen + "\n\n¿Confirmar cierre de caja?"):
                return

            hora_cierre = datetime.now().strftime("%H:%M:%S")
            ejecutar(
                """
                UPDATE caja
                SET hora_cierre = ?, capital_final = ?, total_ventas = ?
                WHERE id = ?
                """,
                (hora_cierre, capital_final, total_ventas, id_caja)
            )
            texto = armar_texto_reporte_diario(usuario)
            imprimir_texto(texto)
            messagebox.showinfo("Cerrado", "Caja cerrada e impresos los reportes.")


        
        CashCountWindow(ventana, mode="cierre", expected_total=capital_esperado, callback=al_cerrar)
        
    tk.Button(ventana, text="← Volver", bg="#CCCCCC", command=lambda: [ventana.destroy(), ventana_principal.deiconify()]).pack(anchor="nw", padx=10, pady=10)
    tk.Button(ventana, text="Cerrar Caja", bg="#D32F2F", fg="white", command=cerrar_caja).pack(anchor="nw", padx=10, pady=(50,10))

    categorias_rows = consultar_todos("SELECT DISTINCT categoria FROM productos")
    categorias = [row[0] for row in categorias_rows]



    for cat in categorias:
        btn = styled_button(
            frame_categorias,
            text=cat,
            bg_color="#1976D2",
            command=lambda c=cat: cargar_productos(c),
            width=18,
            height=2
        )
        btn.pack(padx=5, pady=5)

    if categorias:
        cargar_productos(categorias[0])
        
    ventana.mainloop()
