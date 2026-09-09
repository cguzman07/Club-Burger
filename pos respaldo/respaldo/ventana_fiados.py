import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import customtkinter as ctk

from database import consultar_todos, ejecutar
import tema_caja as tema
import responsive as resp
import animaciones as anim
import fondos


def ventana_ver_fiados(ventana_principal=None, usuario=None):
    """
    Ventana para ver, abonar y eliminar fiados.
    - Agrupa por cliente para evitar duplicados.
    - Abonos se registran en pagos_fiados apuntando al fiado más reciente del cliente.
    - Eliminar fiado borra TODOS los fiados del cliente solo si no hay saldo pendiente.
    """
    tema.apply_theme()
    tema.style_treeview()

    ventana = ctk.CTkToplevel()
    ventana.title("Fiados - Pagos Pendientes")
    ventana.configure(fg_color="#1A120C")
    fondos.aplicar(ventana, estilo="fiados")
    resp.fit(ventana, width_ratio=0.78, height_ratio=0.72, min_w=700, min_h=460, resizable=True)
    ventana.after(100, lambda: fondos.asegurar_al_fondo(ventana))
    ventana.after(150, lambda: fondos.labels_transparantes(ventana))

    if ventana_principal:
        ventana_principal.withdraw()

        def al_cerrar():
            try:
                ventana_principal.deiconify()
            except Exception:
                pass
            ventana.destroy()

        ventana.protocol("WM_DELETE_WINDOW", al_cerrar)
    else:
        ventana.protocol("WM_DELETE_WINDOW", ventana.destroy)

    header = ctk.CTkFrame(ventana, fg_color=tema.BG_PANEL, corner_radius=0, height=64)
    header.pack(fill="x")
    header.pack_propagate(False)
    title_lbl = tema.label(header, "Fiados · Pagos pendientes", font=tema.FONT_TITLE)
    title_lbl.pack(side="left", padx=20, pady=14)

    table_wrap = tema.panel(ventana)
    table_wrap.pack(fill="both", expand=True, padx=16, pady=16)

    frame_tabla = tk.Frame(table_wrap, bg=tema.BG_PANEL)
    frame_tabla.pack(fill="both", expand=True, padx=8, pady=8)

    columnas = ("cliente", "adeudado", "abonado", "saldo")
    tree = ttk.Treeview(frame_tabla, columns=columnas, show="headings", height=14, style="Dark.Treeview")

    headers = [
        ("cliente", "Cliente", 240, "w"),
        ("adeudado", "Total Adeudado", 150, "e"),
        ("abonado", "Total Abonado", 150, "e"),
        ("saldo", "Saldo Pendiente", 150, "e"),
    ]
    for col, txt, width, anchor in headers:
        tree.heading(col, text=txt)
        tree.column(col, width=width, anchor=anchor)

    vsb = ttk.Scrollbar(frame_tabla, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(frame_tabla, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")

    frame_tabla.rowconfigure(0, weight=1)
    frame_tabla.columnconfigure(0, weight=1)

    def query_resumen_por_cliente():
        sql = """
            SELECT
                t.cliente,
                t.total_adeudado,
                IFNULL(a.total_abonos, 0) AS total_abonos,
                (t.total_adeudado - IFNULL(a.total_abonos, 0)) AS saldo_pendiente
            FROM (
                SELECT f.nombre_cliente AS cliente,
                       SUM(f.monto_pendiente) AS total_adeudado
                FROM fiados f
                GROUP BY f.nombre_cliente
            ) AS t
            LEFT JOIN (
                SELECT f.nombre_cliente AS cliente,
                       SUM(p.monto_pagado) AS total_abonos
                FROM fiados f
                JOIN pagos_fiados p ON p.fiado_id = f.id
                GROUP BY f.nombre_cliente
            ) AS a ON a.cliente = t.cliente
            WHERE (t.total_adeudado - IFNULL(a.total_abonos, 0)) > 0
            ORDER BY t.cliente COLLATE NOCASE
        """
        return consultar_todos(sql)

    def obtener_saldo_cliente(cliente: str):
        rows = consultar_todos(
            """
            SELECT
                t.total_adeudado,
                IFNULL(a.total_abonos, 0) AS total_abonos,
                (t.total_adeudado - IFNULL(a.total_abonos, 0)) AS saldo_pendiente
            FROM (
                SELECT SUM(f.monto_pendiente) AS total_adeudado
                FROM fiados f
                WHERE f.nombre_cliente = ?
            ) AS t
            LEFT JOIN (
                SELECT SUM(p.monto_pagado) AS total_abonos
                FROM fiados f
                JOIN pagos_fiados p ON p.fiado_id = f.id
                WHERE f.nombre_cliente = ?
            ) AS a ON 1=1
            """,
            (cliente, cliente),
        )
        if not rows or rows[0]["total_adeudado"] is None:
            return 0.0, 0.0, 0.0
        r = rows[0]
        return float(r["total_adeudado"] or 0), float(r["total_abonos"] or 0), float(r["saldo_pendiente"] or 0)

    def fiado_mas_reciente_id(cliente: str):
        rows = consultar_todos(
            "SELECT id FROM fiados WHERE nombre_cliente = ? ORDER BY id DESC LIMIT 1",
            (cliente,),
        )
        return rows[0]["id"] if rows else None

    def fiado_ids_del_cliente(cliente: str):
        rows = consultar_todos("SELECT id FROM fiados WHERE nombre_cliente = ?", (cliente,))
        return [r["id"] for r in rows]

    def cargar_fiados():
        tree.delete(*tree.get_children())
        fiados = query_resumen_por_cliente()
        for row in fiados:
            tree.insert(
                "",
                "end",
                values=(
                    row["cliente"],
                    f"${row['total_adeudado']:,.2f}",
                    f"${row['total_abonos']:,.2f}",
                    f"${row['saldo_pendiente']:,.2f}",
                ),
            )

    cargar_fiados()

    def registrar_abono():
        seleccion = tree.selection()
        if not seleccion:
            messagebox.showwarning("Atención", "Seleccione un cliente para abonar.")
            return

        cliente = tree.item(seleccion[0])["values"][0]

        total_adeudado, total_abonos, saldo_pend = obtener_saldo_cliente(cliente)
        if saldo_pend <= 0:
            messagebox.showinfo("Sin saldo", f"{cliente} no tiene saldo pendiente.")
            cargar_fiados()
            return

        abono_str = simpledialog.askstring(
            "Registrar Abono",
            f"Ingrese monto a abonar para {cliente}",
            parent=ventana,
        )
        if abono_str is None:
            return

        try:
            abono = float(str(abono_str).replace(",", "."))
            if abono <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Error", "Monto inválido.")
            return

        if abono > saldo_pend:
            messagebox.showwarning(
                "Atención",
                f"El abono supera el saldo pendiente (${saldo_pend:,.2f}).",
            )
            return

        fiado_id = fiado_mas_reciente_id(cliente)
        if not fiado_id:
            messagebox.showerror("Error", "No se encontró un fiado asociado a este cliente.")
            return

        ejecutar(
            "INSERT INTO pagos_fiados (fiado_id, monto_pagado) VALUES (?, ?)",
            (fiado_id, abono),
        )

        _, _, nuevo_saldo = obtener_saldo_cliente(cliente)

        if nuevo_saldo <= 0:
            ids = fiado_ids_del_cliente(cliente)
            if ids:
                placeholders = ",".join("?" for _ in ids)
                ejecutar(f"DELETE FROM pagos_fiados WHERE fiado_id IN ({placeholders})", tuple(ids))
                ejecutar("DELETE FROM fiados WHERE nombre_cliente = ?", (cliente,))
            messagebox.showinfo("Pago completado", f"{cliente} ya no tiene saldo pendiente.")
        else:
            messagebox.showinfo("Abono registrado", f"Se registró un abono de ${abono:,.2f} para {cliente}.")

        cargar_fiados()

    def eliminar_fiado():
        seleccion = tree.selection()
        if not seleccion:
            messagebox.showwarning("Atención", "Seleccione un cliente para eliminar.")
            return

        cliente = tree.item(seleccion[0])["values"][0]

        _, _, saldo_pend = obtener_saldo_cliente(cliente)
        if saldo_pend > 0:
            messagebox.showwarning("Atención", "No se puede eliminar: el cliente tiene saldo pendiente.")
            return

        if not messagebox.askyesno("Confirmar", f"¿Eliminar TODOS los fiados de {cliente}?"):
            return

        ids = fiado_ids_del_cliente(cliente)
        if ids:
            placeholders = ",".join("?" for _ in ids)
            ejecutar(f"DELETE FROM pagos_fiados WHERE fiado_id IN ({placeholders})", tuple(ids))
            ejecutar("DELETE FROM fiados WHERE nombre_cliente = ?", (cliente,))

        messagebox.showinfo("Eliminado", f"Se eliminaron los fiados de {cliente}.")
        cargar_fiados()

    frame_botones = ctk.CTkFrame(ventana, fg_color="transparent")
    frame_botones.pack(fill="x", padx=16, pady=(0, 16))

    btn_abonar = tema.button(
        frame_botones, "Registrar Abono", tema.ACCENT_GREEN, command=registrar_abono, height=42
    )
    btn_abonar.pack(side="left", padx=(0, 8))
    btn_eliminar = tema.button(
        frame_botones, "Eliminar Fiado", tema.ACCENT_RED, command=eliminar_fiado, height=42
    )
    btn_eliminar.pack(side="left", padx=8)
    btn_cerrar = tema.button(
        frame_botones,
        "Cerrar",
        tema.ACCENT_GRAY,
        command=(
            (lambda: (ventana_principal.deiconify(), ventana.destroy()))
            if ventana_principal
            else ventana.destroy
        ),
        height=42,
    )
    btn_cerrar.pack(side="right")

    anim.soft_entrance(
        ventana,
        title=title_lbl,
        panels=[table_wrap],
        buttons=[btn_abonar, btn_eliminar, btn_cerrar],
        accent=tema.ACCENT_ORANGE,
    )
