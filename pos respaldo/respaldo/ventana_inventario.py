import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import customtkinter as ctk

from database import inicializar_db
import tema_caja as tema
import responsive as resp
import animaciones as anim
from iconos import apply_window_icon
import fondos


def ventana_inventario(usuario, ventana_principal):
    ventana_principal.withdraw()
    tema.apply_theme()
    tema.style_treeview()

    ventana = ctk.CTkToplevel()
    ventana.title("Inventario de Productos")
    ventana.configure(fg_color="#1A120C")
    apply_window_icon(ventana)
    fondos.aplicar(ventana, estilo="admin")
    resp.fit(ventana, width_ratio=0.88, height_ratio=0.86, min_w=780, min_h=520, resizable=True)
    ventana.after(100, lambda: fondos.asegurar_al_fondo(ventana))
    ventana.after(150, lambda: fondos.labels_transparantes(ventana))

    def cargar_productos():
        for fila in tabla.get_children():
            tabla.delete(fila)
        conn = sqlite3.connect("datos_pos.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, categoria, precio, stock, stock_inicial FROM productos")

        for row in cursor.fetchall():
            id_, nombre, categoria, precio, stock, stock_inicial = row
            stock_mostrar = f"{stock}/{stock_inicial if stock_inicial else stock}"
            tabla.insert("", tk.END, values=(id_, nombre, categoria, precio, stock_mostrar))

        conn.close()

    def agregar_producto():
        def guardar():
            nombre = entry_nombre.get()
            categoria = entry_categoria.get()
            try:
                precio = float(entry_precio.get())
                stock = int(entry_stock.get())
            except ValueError:
                messagebox.showerror("Error", "Precio y stock deben ser numéricos.")
                return
            if not nombre:
                messagebox.showerror("Error", "El nombre no puede estar vacío.")
                return

            conn = sqlite3.connect("datos_pos.db")
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO productos (nombre, categoria, precio, stock, stock_inicial) VALUES (?, ?, ?, ?, ?)",
                (nombre, categoria, precio, stock, stock),
            )
            conn.commit()
            conn.close()
            ventana_agregar.destroy()
            cargar_productos()

        ventana_agregar = ctk.CTkToplevel(ventana)
        ventana_agregar.title("Agregar Producto")
        ventana_agregar.configure(fg_color=tema.BG_APP)
        resp.fit_dialog(ventana_agregar, width_ratio=0.32, height_ratio=0.42, min_w=340, min_h=300)
        ventana_agregar.grab_set()

        card = tema.card(ventana_agregar)
        card.pack(fill="both", expand=True, padx=16, pady=16)
        tema.label(card, "Agregar producto", font=tema.FONT_HEADER).pack(anchor="w", padx=16, pady=(12, 10))

        campos = ["Nombre", "Categoría", "Precio", "Stock"]
        entradas = []
        for campo in campos:
            tema.label(card, campo, font=tema.FONT_SMALL, color=tema.TEXT_DIM).pack(anchor="w", padx=16)
            e = tema.entry(card)
            e.pack(fill="x", padx=16, pady=(2, 8))
            entradas.append(e)

        entry_nombre, entry_categoria, entry_precio, entry_stock = entradas
        tema.button(card, "Guardar", tema.ACCENT_GREEN, command=guardar, height=42).pack(
            fill="x", padx=16, pady=(8, 16)
        )

    def editar_producto():
        item = tabla.focus()
        if not item:
            messagebox.showwarning("Advertencia", "Selecciona un producto para editar.")
            return
        datos = tabla.item(item)["values"]
        producto_id, nombre_actual, categoria_actual, precio_actual, stock_actual = datos

        def guardar_cambios():
            nuevo_nombre = entry_nombre.get()
            nueva_categoria = entry_categoria.get()
            try:
                nuevo_precio = float(entry_precio.get())
                nuevo_stock = int(entry_stock.get())
            except ValueError:
                messagebox.showerror("Error", "Precio y stock deben ser numéricos.")
                return

            conn = sqlite3.connect("datos_pos.db")
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE productos SET nombre = ?, categoria = ?, precio = ?, stock = ?, stock_inicial = ? WHERE id = ?",
                (nuevo_nombre, nueva_categoria, nuevo_precio, nuevo_stock, nuevo_stock, producto_id),
            )
            conn.commit()
            conn.close()
            ventana_editar.destroy()
            cargar_productos()

        ventana_editar = ctk.CTkToplevel(ventana)
        ventana_editar.title("Editar Producto")
        ventana_editar.configure(fg_color=tema.BG_APP)
        resp.fit_dialog(ventana_editar, width_ratio=0.32, height_ratio=0.42, min_w=340, min_h=300)
        ventana_editar.grab_set()

        card = tema.card(ventana_editar)
        card.pack(fill="both", expand=True, padx=16, pady=16)
        tema.label(card, "Editar producto", font=tema.FONT_HEADER).pack(anchor="w", padx=16, pady=(12, 10))

        etiquetas = ["Nombre", "Categoría", "Precio", "Stock"]
        valores = [nombre_actual, categoria_actual, precio_actual, stock_actual]
        entradas = []
        for etiqueta, valor in zip(etiquetas, valores):
            tema.label(card, etiqueta, font=tema.FONT_SMALL, color=tema.TEXT_DIM).pack(anchor="w", padx=16)
            e = tema.entry(card)
            e.insert(0, valor)
            e.pack(fill="x", padx=16, pady=(2, 8))
            entradas.append(e)

        entry_nombre, entry_categoria, entry_precio, entry_stock = entradas
        tema.button(card, "Guardar cambios", tema.ACCENT_BLUE, command=guardar_cambios, height=42).pack(
            fill="x", padx=16, pady=(8, 16)
        )

    def eliminar_producto():
        item = tabla.focus()
        if not item:
            messagebox.showwarning("Advertencia", "Selecciona un producto para eliminar.")
            return
        datos = tabla.item(item)["values"]
        producto_id = datos[0]
        respuesta = messagebox.askyesno("Confirmar", f"¿Eliminar el producto '{datos[1]}'?")
        if respuesta:
            conn = sqlite3.connect("datos_pos.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM productos WHERE id = ?", (producto_id,))
            conn.commit()
            conn.close()
            cargar_productos()

    # Header
    header = ctk.CTkFrame(ventana, fg_color=tema.BG_PANEL, corner_radius=0, height=64)
    header.pack(fill="x")
    header.pack_propagate(False)
    btn_volver = tema.button(
        header,
        "← Volver",
        tema.ACCENT_GRAY,
        command=lambda: [ventana.destroy(), ventana_principal.deiconify()],
        width=110,
        height=36,
    )
    btn_volver.pack(side="left", padx=16, pady=14)
    title_lbl = tema.label(header, "Inventario de Productos", font=tema.FONT_TITLE)
    title_lbl.pack(side="left", padx=8)

    # Tabla
    table_wrap = tema.panel(ventana)
    table_wrap.pack(fill="both", expand=True, padx=16, pady=16)

    contenedor_tabla = tk.Frame(table_wrap, bg=tema.BG_PANEL)
    contenedor_tabla.pack(expand=True, fill="both", padx=8, pady=8)

    scroll_y = ttk.Scrollbar(contenedor_tabla, orient="vertical")
    scroll_y.pack(side="right", fill="y")

    columnas = ("ID", "Nombre", "Categoría", "Precio", "Stock")
    tabla = ttk.Treeview(
        contenedor_tabla,
        columns=columnas,
        show="headings",
        yscrollcommand=scroll_y.set,
        style="Dark.Treeview",
    )
    scroll_y.config(command=tabla.yview)

    for col in columnas:
        tabla.heading(col, text=col)
        tabla.column(col, width=150, anchor="center")

    tabla.pack(expand=True, fill="both")

    def _on_mousewheel(event):
        tabla.yview_scroll(int(-1 * (event.delta / 120)), "units")

    tabla.bind("<MouseWheel>", _on_mousewheel)
    tabla.bind("<Button-4>", lambda e: tabla.yview_scroll(-1, "units"))
    tabla.bind("<Button-5>", lambda e: tabla.yview_scroll(1, "units"))

    # Botones
    frame_botones = ctk.CTkFrame(ventana, fg_color="transparent")
    frame_botones.pack(fill="x", padx=16, pady=(0, 16))

    botones = [
        ("🔄 Actualizar", cargar_productos, tema.ACCENT_GRAY),
        ("➕ Agregar", agregar_producto, tema.ACCENT_GREEN),
        ("✏️ Editar", editar_producto, tema.ACCENT_BLUE),
        ("🗑️ Eliminar", eliminar_producto, tema.ACCENT_RED),
    ]
    botones_ui = []
    for i, (texto, comando, color) in enumerate(botones):
        b = tema.button(frame_botones, texto, color, command=comando, height=42)
        b.grid(row=0, column=i, padx=6, sticky="ew")
        frame_botones.grid_columnconfigure(i, weight=1)
        botones_ui.append(b)

    inicializar_db()
    cargar_productos()

    anim.soft_entrance(
        ventana,
        title=title_lbl,
        panels=[table_wrap],
        buttons=[btn_volver] + botones_ui,
        accent=tema.ACCENT_GREEN,
    )
