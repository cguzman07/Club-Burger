"""
Saludos de bienvenida y despedida (solo experiencia / apariencia).
"""
import random
import customtkinter as ctk
import tema_caja as tema
import fechahora as fh
import fondos


_BIENVENIDAS = [
    "Qué bueno tenerte aquí. ¡Vamos a hacer un gran turno!",
    "Tu energía importa. Hoy los clientes lo van a notar.",
    "Listos para vender con buena actitud. ¡Tú puedes!",
    "Bienvenido de nuevo. El local se siente mejor contigo.",
    "Hoy es un excelente día para un servicio impecable.",
]

_DESPEDIDAS = [
    "Gracias por tu turno. Descansa y vuelve con esa misma sonrisa.",
    "Excelente trabajo hoy. ¡Nos vemos en el próximo turno!",
    "Turno cerrado. Cuídate mucho — eres clave en Club Burger.",
    "Gracias por tu dedicación. ¡Que tengas un resto de día genial!",
    "Hasta pronto. El equipo agradece tu esfuerzo de hoy.",
]


def _nombre_bonito(usuario: str) -> str:
    return (usuario or "amigo").strip().title() or "Amigo"


def _saludo_hora() -> str:
    h = fh.ahora().hour
    if h < 12:
        return "Buenos días"
    if h < 19:
        return "Buenas tardes"
    return "Buenas noches"


def _dialogo(titulo, linea1, linea2, boton_texto, color_boton, parent=None):
    """Modal con letras sobre la foto (sin cajas negras)."""
    win = ctk.CTkToplevel(parent) if parent else ctk.CTkToplevel()
    win.title(titulo)
    win.configure(fg_color="#1A120C")
    win.resizable(False, False)
    win.geometry("420x280")
    win.attributes("-topmost", True)
    fondos.aplicar(win, estilo="saludo")

    win.update_idletasks()
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    x = max(0, (sw - 420) // 2)
    y = max(0, (sh - 280) // 2)
    win.geometry(f"420x280+{x}+{y}")

    def _pintar_textos():
        fondos.letrero(
            win,
            "l1",
            linea1,
            210,
            78,
            fill="#FFFFFF",
            font=(tema.FONT_FAMILY, 20, "bold"),
            anchor="n",
            width=360,
            justify="center",
        )
        fondos.letrero(
            win,
            "l2",
            linea2,
            210,
            130,
            fill="#FFE8CC",
            font=(tema.FONT_FAMILY, 13),
            anchor="n",
            width=360,
            justify="center",
        )
        fondos.asegurar_al_fondo(win)

    win.after(60, _pintar_textos)
    win.after(200, _pintar_textos)

    cerrado = {"ok": False}

    def cerrar():
        cerrado["ok"] = True
        win.destroy()

    ctk.CTkButton(
        win,
        text=boton_texto,
        command=cerrar,
        height=44,
        corner_radius=18,
        width=280,
        fg_color=color_boton,
        hover_color=tema.BG_HOVER,
        font=tema.FONT_BTN_LG,
        text_color="#111111" if color_boton == tema.ACCENT_ORANGE else tema.TEXT,
    ).place(relx=0.5, rely=0.82, anchor="center")

    win.protocol("WM_DELETE_WINDOW", cerrar)
    win.grab_set()
    win.focus_force()
    win.wait_window()
    return cerrado["ok"]


def mostrar_bienvenida(usuario: str, rol: str = "cajero", parent=None):
    nombre = _nombre_bonito(usuario)
    rol_txt = (rol or "cajero").capitalize()
    frase = random.choice(_BIENVENIDAS)
    linea1 = f"{_saludo_hora()}, {nombre}"
    linea2 = f"{frase}\n\nHoy: {fh.formatear_corto()}  ·  Rol: {rol_txt}"
    _dialogo(
        "Bienvenida",
        linea1,
        linea2,
        "¡Vamos al turno! →",
        tema.ACCENT_ORANGE,
        parent=parent,
    )


def mostrar_despedida(usuario: str, parent=None):
    nombre = _nombre_bonito(usuario)
    frase = random.choice(_DESPEDIDAS)
    linea1 = f"Hasta pronto, {nombre}"
    linea2 = f"{frase}\n\n{fh.formatear_header()}"
    _dialogo(
        "Despedida",
        linea1,
        linea2,
        "Cerrar sesión",
        tema.ACCENT_GREEN,
        parent=parent,
    )
