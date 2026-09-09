import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from database import consultar_todos, ejecutar
from datetime import datetime

def ventana_ver_fiados(ventana_principal=None, usuario=None):
    ventana = tk.Toplevel()
    ventana.title("Fiados - Pagos Pendientes")
    ventana.geometry("600x400")
    ventana.configure(bg="white")

    columnas = ("cliente", "adeudado", "abonado", "saldo")
    tree = ttk.Treeview(ventana, columns=columnas, show="headings")
    for col, txt, width, anchor in [
        ("cliente", "Cliente", 200, "w"),
        ("adeudado", "Total Adeudado", 120, "e"),
        ("abonado", "Total Abonado", 120, "e"),
        ("saldo", "Saldo Pendiente", 120, "e"),
    ]:
        tree.heading(col, text=txt)
        tree.column(col, width=width, anchor=anchor)

    tree.pack(fill="both", expand=True, padx=10, pady=10)

    def cargar_fiados():
        tree.delete(*tree.get_children())
        fiados = consultar_todos("""
            SELECT cliente, monto_total, monto_pagado, (monto_total - monto_pagado) AS saldo_pendiente
            FROM fiados
            WHERE (monto_total - monto_pagado) > 0
            ORDER BY cliente
        """)
        for row in fiados:
            tree.insert("", "end", values=(
                row["cliente"],
                f"${row['monto_total']:,.2f}",
                f"${row['monto_pagado']:,.2f}",
                f"${row['saldo_pendiente']:,.2f}"
            ))

    cargar_fiados()

    def registrar_abono():
        seleccion = tree.selection()
        if not seleccion:
            messagebox.showwarning("Atención", "Seleccione un cliente para abonar.")
            return
        item = tree.item(seleccion[0])
        cliente = item["values"][0]

        abono_str = simpledialog.askstring("Registrar Abono", f"Ingrese monto a abonar para {cliente}:", parent=ventana)
        if abono_str is None:
            return  # Canceló
        try:
            abono = float(abono_str)
            if abono <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Error", "Monto inválido")
            return

        fila = consultar_todos("SELECT monto_total, monto_pagado FROM fiados WHERE cliente = ?", (cliente,))
        if not fila:
            messagebox.showerror("Error", "Cliente no encontrado en la base de datos")
            return

        monto_total = fila[0]["monto_total"]
        monto_pagado = fila[0]["monto_pagado"]
        saldo_pendiente = monto_total - monto_pagado

        if abono > saldo_pendiente:
            messagebox.showwarning("Atención", f"El abono supera el saldo pendiente (${saldo_pendiente:,.2f}).")
            return

        nuevo_pagado = monto_pagado + abono
        ejecutar("UPDATE fiados SET monto_pagado = ? WHERE cliente = ?", (nuevo_pagado, cliente))
        messagebox.showinfo("Abono registrado", f"Se registró un abono de ${abono:,.2f} para {cliente}.")

        cargar_fiados()

    def eliminar_fiado():
        seleccion = tree.selection()
        if not seleccion:
            messagebox.showwarning("Atención", "Seleccione un cliente para eliminar.")
            return
        item = tree.item(seleccion[0])
        cliente = item["values"][0]

        fila = consultar_todos("SELECT monto_total, monto_pagado FROM fiados WHERE cliente = ?", (cliente,))
        if not fila:
            messagebox.showerror("Error", "Cliente no encontrado en la base de datos")
            return

        monto_total = fila[0]["monto_total"]
        monto_pagado = fila[0]["monto_pagado"]
        saldo_pendiente = monto_total - monto_pagado

        if saldo_pendiente > 0:
            messagebox.showwarning("Atención", "No se puede eliminar un fiado con saldo pendiente.")
            return

        confirmacion = messagebox.askyesno("Confirmar", f"¿Seguro que desea eliminar el fiado de {cliente}?")
        if confirmacion:
            ejecutar("DELETE FROM fiados WHERE cliente = ?", (cliente,))
            messagebox.showinfo("Eliminado", f"Fiado de {cliente} eliminado.")
            cargar_fiados()

    btn_abonar = tk.Button(ventana, text="Registrar Abono", command=registrar_abono, bg="#4CAF50", fg="white")
    btn_abonar.pack(pady=5)

    btn_eliminar = tk.Button(ventana, text="Eliminar Fiado", command=eliminar_fiado, bg="#E53935", fg="white")
    btn_eliminar.pack(pady=5)

    btn_cerrar = tk.Button(ventana, text="Cerrar", command=ventana.destroy)
    btn_cerrar.pack(pady=5)

    if ventana_principal:
        ventana_principal.withdraw()
        def al_cerrar():
            ventana_principal.deiconify()
            ventana.destroy()
        ventana.protocol("WM_DELETE_WINDOW", al_cerrar)
    else:
        ventana.protocol("WM_DELETE_WINDOW", ventana.destroy)
