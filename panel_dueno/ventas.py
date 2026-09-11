"""Registro de ventas remotas en datos_pos.db (misma caja e inventario del POS)."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from snapshot import db_path, leer_estado

METODOS = ("Efectivo", "Nequi", "Daviplata", "Transferencia", "Tarjeta")


class VentaError(Exception):
    def __init__(self, mensaje: str, codigo: int = 400):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


def _factura_path() -> Path:
    return db_path().parent / "numero_factura.txt"


def _siguiente_factura() -> int:
    path = _factura_path()
    try:
        actual = int(path.read_text(encoding="utf-8").strip() or "0")
    except (FileNotFoundError, ValueError):
        actual = 0
    nuevo = actual + 1
    path.write_text(str(nuevo), encoding="utf-8")
    return nuevo


def _revertir_factura(numero: int) -> None:
    path = _factura_path()
    try:
        actual = int(path.read_text(encoding="utf-8").strip() or "0")
    except (FileNotFoundError, ValueError):
        return
    if actual == numero:
        path.write_text(str(max(0, numero - 1)), encoding="utf-8")


def registrar_venta(
    items: list[dict[str, Any]],
    metodo_pago: str,
    recibido: float | None = None,
    nota: str = "",
    imprimir: bool = True,
) -> dict[str, Any]:
    metodo = (metodo_pago or "").strip()
    if not metodo or len(metodo) > 40:
        raise VentaError("Método de pago no válido.")

    lineas: list[dict[str, Any]] = []
    for crudo in items or []:
        try:
            pid = int(crudo.get("id"))
            cantidad = int(crudo.get("cantidad"))
        except (TypeError, ValueError):
            raise VentaError("Hay un producto con cantidad inválida.") from None
        if cantidad < 1 or cantidad > 99:
            raise VentaError("La cantidad debe estar entre 1 y 99.")
        lineas.append({"id": pid, "cantidad": cantidad})
    if not lineas:
        raise VentaError("Agrega al menos un producto.")

    agrupado: dict[int, int] = {}
    for linea in lineas:
        agrupado[linea["id"]] = agrupado.get(linea["id"], 0) + linea["cantidad"]

    path = db_path()
    if not path.exists():
        raise VentaError("No se encontró datos_pos.db.", 500)

    conn = sqlite3.connect(str(path), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=8000")
    factura = None
    try:
        conn.execute("BEGIN IMMEDIATE")
        caja = conn.execute(
            "SELECT * FROM caja WHERE hora_cierre IS NULL OR hora_cierre = '' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if caja is None:
            raise VentaError("La caja está cerrada. Ábrela en el computador del restaurante.", 409)

        detalle = []
        total = 0.0
        for pid, cantidad in agrupado.items():
            prod = conn.execute("SELECT * FROM productos WHERE id=?", (pid,)).fetchone()
            if prod is None:
                raise VentaError("Un producto del pedido ya no existe.")
            stock = int(prod["stock"] or 0)
            if stock < cantidad:
                raise VentaError(
                    f"No hay suficiente {prod['nombre']}. Quedan {stock}.",
                    409,
                )
            precio = float(prod["precio"] or 0)
            subtotal = round(precio * cantidad, 2)
            total += subtotal
            detalle.append(
                {
                    "id": pid,
                    "nombre": prod["nombre"],
                    "cantidad": cantidad,
                    "precio": precio,
                    "subtotal": subtotal,
                    "stock_antes": stock,
                }
            )
            cambiado = conn.execute(
                "UPDATE productos SET stock = stock - ? WHERE id=? AND stock >= ?",
                (cantidad, pid, cantidad),
            )
            if cambiado.rowcount != 1:
                raise VentaError(f"No hay suficiente {prod['nombre']}.", 409)

        total = round(total, 2)
        rec = float(recibido) if recibido is not None else None
        cambio = None
        if metodo == "Efectivo" and rec is not None:
            if rec < total:
                raise VentaError("El valor recibido es menor al total.")
            cambio = round(rec - total, 2)

        factura = _siguiente_factura()
        extra = "Remoto"
        if nota.strip():
            extra = f"Remoto · {nota.strip()[:80]}"
        extra = f"{extra} · Factura {factura}"
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for fila in detalle:
            conn.execute(
                """
                INSERT INTO ventas (
                    fecha, producto_id, nombre_producto, cantidad,
                    precio_unitario, total, metodo_pago, id_caja, nota
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ahora,
                    fila["id"],
                    fila["nombre"],
                    fila["cantidad"],
                    fila["precio"],
                    fila["subtotal"],
                    metodo,
                    caja["id"],
                    extra,
                ),
            )
        conn.commit()
    except VentaError:
        conn.rollback()
        if factura is not None:
            _revertir_factura(factura)
        raise
    except sqlite3.OperationalError as exc:
        conn.rollback()
        if factura is not None:
            _revertir_factura(factura)
        raise VentaError("La caja está ocupada. Intenta de nuevo en un momento.", 409) from exc
    finally:
        conn.close()

    try:
        from nube_sync import _cliente
        from libro import sincronizar_libro

        sincronizar_libro(_cliente())
    except Exception:
        pass

    impreso = False
    error_impresion = None
    if imprimir:
        from ticket import imprimir_ticket

        impreso, error_impresion = imprimir_ticket(
            detalle=detalle,
            total=total,
            metodo_pago=metodo,
            recibido=rec,
            cambio=cambio,
            factura=factura,
            cajero=caja["usuario"],
        )

    return {
        "ok": True,
        "factura": factura,
        "total": total,
        "metodo_pago": metodo,
        "recibido": rec,
        "cambio": cambio,
        "items": detalle,
        "cajero": caja["usuario"],
        "impreso": impreso,
        "error_impresion": error_impresion,
        "estado": leer_estado(),
    }
