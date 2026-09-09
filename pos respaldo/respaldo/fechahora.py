"""
Fecha y hora local del sistema (POS).
Evita UTC de SQLite DATE('now') — en Colombia eso desfasaba el día cerca de medianoche.
"""
from datetime import datetime

# Nombres en español (sin depender de locale del SO)
_DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
_MESES = (
    "ene", "feb", "mar", "abr", "may", "jun",
    "jul", "ago", "sep", "oct", "nov", "dic",
)
_MESES_FULL = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)


def ahora() -> datetime:
    """Instante local actual del equipo."""
    return datetime.now()


def fecha_sql(dt: datetime | None = None) -> str:
    """YYYY-MM-DD para guardar en BD."""
    return (dt or ahora()).strftime("%Y-%m-%d")


def hora_sql(dt: datetime | None = None) -> str:
    """HH:MM:SS para guardar en BD."""
    return (dt or ahora()).strftime("%H:%M:%S")


def datetime_sql(dt: datetime | None = None) -> str:
    """YYYY-MM-DD HH:MM:SS para ventas / tickets."""
    return (dt or ahora()).strftime("%Y-%m-%d %H:%M:%S")


def ano_mes_sql(dt: datetime | None = None) -> str:
    return (dt or ahora()).strftime("%Y-%m")


def formatear_largo(dt: datetime | None = None) -> str:
    """Ej: miércoles 15 de julio de 2026"""
    d = dt or ahora()
    return f"{_DIAS[d.weekday()]} {d.day} de {_MESES_FULL[d.month - 1]} de {d.year}"


def formatear_corto(dt: datetime | None = None) -> str:
    """Ej: mié 15 jul 2026"""
    d = dt or ahora()
    return f"{_DIAS[d.weekday()][:3]} {d.day} {_MESES[d.month - 1]} {d.year}"


def formatear_hora(dt: datetime | None = None) -> str:
    """Ej: 10:54:07 a. m. estilo 12h amigable, o 24h claro."""
    d = dt or ahora()
    return d.strftime("%I:%M:%S %p").lstrip("0").replace("AM", "a. m.").replace("PM", "p. m.")


def formatear_reloj(dt: datetime | None = None) -> str:
    """Reloj compacto tipo header: 10:54"""
    return (dt or ahora()).strftime("%H:%M")


def formatear_header(dt: datetime | None = None) -> str:
    """Línea completa para barra superior."""
    d = dt or ahora()
    return f"{formatear_corto(d)}  ·  {formatear_reloj(d)}"
