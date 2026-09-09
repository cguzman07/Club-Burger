import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
import customtkinter as ctk

import tema_caja as tema
import responsive as resp
import animaciones as anim
from iconos import apply_window_icon
import fondos


def ventana_gestion_usuarios(usuario_activo, ventana_anterior):
    ventana_anterior.withdraw()
    tema.apply_theme()
    tema.style_treeview()

    ventana = ctk.CTkToplevel()
    ventana.title("Gestión de Usuarios")
    ventana.configure(fg_color="#1A120C")
    apply_window_icon(ventana)
    fondos.aplicar(ventana, estilo="admin")
    resp.fit(ventana, width_ratio=0.82, height_ratio=0.84, min_w=760, min_h=520, resizable=True)
    ventana.after(100, lambda: fondos.asegurar_al_fondo(ventana))
    ventana.after(150, lambda: fondos.labels_transparantes(ventana))

    def volver():
        ventana.destroy()
        ventana_anterior.deiconify()

    header = ctk.CTkFrame(ventana, fg_color=tema.BG_PANEL, corner_radius=0, height=64)
    header.pack(fill="x")
    header.pack_propagate(False)
    btn_volver = tema.button(header, "← Volver", tema.ACCENT_GRAY, command=volver, width=110, height=36)
    btn_volver.pack(side="left", padx=16, pady=14)
    title_lbl = tema.label(header, "Gestión de Usuarios", font=tema.FONT_TITLE)
    title_lbl.pack(side="left", padx=8)

    table_wrap = tema.panel(ventana)
    table_wrap.pack(fill="both", expand=True, padx=16, pady=(16, 8))

    tree_host = tk.Frame(table_wrap, bg=tema.BG_PANEL)
    tree_host.pack(fill="both", expand=True, padx=8, pady=8)

    tree = ttk.Treeview(
        tree_host,
        columns=("ID", "Usuario", "Rol"),
        show="headings",
        height=10,
        style="Dark.Treeview",
    )
    for col in ("ID", "Usuario", "Rol"):
        tree.heading(col, text=col)
        tree.column(col, anchor="center", width=160)
    tree.pack(padx=4, pady=4, fill="both", expand=True)

    def cargar_usuarios():
        for row in tree.get_children():
            tree.delete(row)
        conn = sqlite3.connect("datos_pos.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, usuario, rol FROM usuarios")
        for fila in cursor.fetchall():
            tree.insert("", "end", values=fila)
        conn.close()

    cargar_usuarios()

    form = tema.card(ventana)
    form.pack(fill="x", padx=16, pady=8)
    tema.label(form, "Agregar nuevo usuario", font=tema.FONT_HEADER).pack(anchor="w", padx=16, pady=(14, 8))

    grid = ctk.CTkFrame(form, fg_color="transparent")
    grid.pack(fill="x", padx=16, pady=(0, 8))

    tema.label(grid, "Usuario", font=tema.FONT_SMALL, color=tema.TEXT_DIM).grid(row=0, column=0, sticky="w")
    entry_usuario = tema.entry(grid, width=200)
    entry_usuario.grid(row=1, column=0, padx=(0, 12), pady=4)

    tema.label(grid, "Contraseña", font=tema.FONT_SMALL, color=tema.TEXT_DIM).grid(row=0, column=1, sticky="w")
    entry_contrasena = tema.entry(grid, show="*", width=200)
    entry_contrasena.grid(row=1, column=1, padx=(0, 12), pady=4)

    tema.label(grid, "Rol", font=tema.FONT_SMALL, color=tema.TEXT_DIM).grid(row=0, column=2, sticky="w")
    combo_rol = ctk.CTkComboBox(
        grid,
        values=["admin", "cajero"],
        width=160,
        height=36,
        fg_color=tema.BG_INPUT,
        border_width=0,
        button_color=tema.ACCENT_ORANGE,
        corner_radius=tema.RADIUS_SM,
        font=tema.FONT_BODY,
    )
    combo_rol.set("cajero")
    combo_rol.grid(row=1, column=2, pady=4)

    def agregar_usuario():
        usuario = entry_usuario.get().strip()
        contrasena = entry_contrasena.get().strip()
        rol = combo_rol.get().strip()

        if not usuario or not contrasena or not rol:
            messagebox.showwarning("Advertencia", "Completa todos los campos.")
            return

        conn = sqlite3.connect("datos_pos.db")
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO usuarios (usuario, contrasena, rol) VALUES (?, ?, ?)",
                (usuario, contrasena, rol),
            )
            conn.commit()
            messagebox.showinfo("Éxito", "Usuario agregado correctamente.")
            cargar_usuarios()
            entry_usuario.delete(0, tk.END)
            entry_contrasena.delete(0, tk.END)
            combo_rol.set("cajero")
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Ese nombre de usuario ya existe.")
        finally:
            conn.close()

    def eliminar_usuario():
        seleccionado = tree.focus()
        if not seleccionado:
            messagebox.showwarning("Advertencia", "Selecciona un usuario para eliminar.")
            return

        valores = tree.item(seleccionado, "values")
        id_usuario = valores[0]
        nombre_usuario = valores[1]

        if nombre_usuario == usuario_activo:
            messagebox.showerror("Error", "No puedes eliminar al usuario activo.")
            return

        confirm = messagebox.askyesno("Confirmar", f"¿Estás seguro de eliminar al usuario '{nombre_usuario}'?")
        if confirm:
            conn = sqlite3.connect("datos_pos.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM usuarios WHERE id=?", (id_usuario,))
            conn.commit()
            conn.close()
            cargar_usuarios()
            messagebox.showinfo("Eliminado", "Usuario eliminado correctamente.")

    def cambiar_contrasena():
        seleccionado = tree.focus()
        if not seleccionado:
            messagebox.showwarning("Advertencia", "Selecciona un usuario para cambiar la contraseña.")
            return

        valores = tree.item(seleccionado, "values")
        id_usuario = valores[0]
        nombre_usuario = valores[1]

        nueva_contrasena = simpledialog.askstring(
            "Nueva Contraseña",
            f"Ingrese nueva contraseña para '{nombre_usuario}':",
            show="*",
        )
        if nueva_contrasena:
            conn = sqlite3.connect("datos_pos.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE usuarios SET contrasena=? WHERE id=?", (nueva_contrasena, id_usuario))
            conn.commit()
            conn.close()
            messagebox.showinfo("Éxito", "Contraseña actualizada correctamente.")

    def cambiar_usuario():
        seleccionado = tree.focus()
        if not seleccionado:
            messagebox.showwarning("Advertencia", "Selecciona un usuario para cambiar el nombre.")
            return

        valores = tree.item(seleccionado, "values")
        id_usuario = valores[0]
        nombre_actual = valores[1]

        nuevo_nombre = simpledialog.askstring(
            "Cambiar Usuario",
            f"Ingrese nuevo nombre para '{nombre_actual}':",
        )
        if nuevo_nombre:
            nuevo_nombre = nuevo_nombre.strip()
            if not nuevo_nombre:
                messagebox.showwarning("Advertencia", "El nombre no puede estar vacío.")
                return

            conn = sqlite3.connect("datos_pos.db")
            cursor = conn.cursor()
            try:
                cursor.execute("UPDATE usuarios SET usuario=? WHERE id=?", (nuevo_nombre, id_usuario))
                conn.commit()
                messagebox.showinfo("Éxito", "Nombre de usuario actualizado correctamente.")
                cargar_usuarios()
            except sqlite3.IntegrityError:
                messagebox.showerror("Error", "Ese nombre de usuario ya existe.")
            finally:
                conn.close()

    frame_botones = ctk.CTkFrame(ventana, fg_color="transparent")
    frame_botones.pack(fill="x", padx=16, pady=(4, 16))

    acciones = [
        ("➕ Agregar", agregar_usuario, tema.ACCENT_GREEN),
        ("🗑️ Eliminar", eliminar_usuario, tema.ACCENT_RED),
        ("🔑 Contraseña", cambiar_contrasena, tema.ACCENT_BLUE),
        ("✏️ Usuario", cambiar_usuario, tema.ACCENT_ORANGE),
    ]
    botones_ui = []
    for i, (texto, cmd, color) in enumerate(acciones):
        b = tema.button(frame_botones, texto, color, command=cmd, height=42)
        b.grid(row=0, column=i, padx=6, sticky="ew")
        frame_botones.grid_columnconfigure(i, weight=1)
        botones_ui.append(b)

    anim.soft_entrance(
        ventana,
        title=title_lbl,
        panels=[table_wrap, form],
        buttons=[btn_volver] + botones_ui,
        accent=tema.ACCENT_PURPLE,
    )
