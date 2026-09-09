"""Panel del dueño: API + WebSocket en tiempo real. No modifica Club Burger.exe."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import secrets
import socket
import time
from contextlib import asynccontextmanager
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import qrcode
import qrcode.image.svg
import uvicorn
from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from snapshot import leer_estado
from ticket import _printer_name
from ventas import METODOS, VentaError, registrar_venta
from nube_sync import ciclo_nube, nube_activa, url_publica

ROOT = Path(__file__).resolve().parent
APP_ROOT = ROOT.parent
STATIC = ROOT / "static"
TEMPLATES_DIR = ROOT / "templates"
CONFIG_PATH = ROOT / "config.json"
PUERTO = int(os.environ.get("PANEL_PUERTO", "5050"))
PIN_ITERS = 40_000

_tokens: dict[str, float] = {}
_intentos: dict[str, list[float]] = {}
_clientes_ws: set[WebSocket] = set()
_ultima_firma = ""
_config: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    cargar_config()
    tareas = [
        asyncio.create_task(bucle_vigilancia()),
        asyncio.create_task(bucle_nube()),
    ]
    yield
    for tarea in tareas:
        tarea.cancel()


app = FastAPI(
    title="Club Burger · Panel del dueño",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=STATIC), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _hash_pin(pin: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt.encode("utf-8"), PIN_ITERS).hex()


def cargar_config() -> dict[str, Any]:
    global _config
    if CONFIG_PATH.exists():
        _config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if "pin" in _config and "pin_hash" not in _config:
            salt = secrets.token_hex(16)
            _config["pin_hash"] = _hash_pin(str(_config.pop("pin")), salt)
            _config["salt"] = salt
            _config["iters"] = PIN_ITERS
            guardar_config()
        elif _config.get("pin_plano") and _config.get("iters") != PIN_ITERS:
            salt = _config.get("salt") or secrets.token_hex(16)
            _config["salt"] = salt
            _config["pin_hash"] = _hash_pin(str(_config["pin_plano"]), salt)
            _config["iters"] = PIN_ITERS
            guardar_config()
        if "stock_minimo" not in _config:
            _config["stock_minimo"] = 5
            guardar_config()
        if "metodos_pago" not in _config:
            _config["metodos_pago"] = list(METODOS)
            guardar_config()
        return _config

    pin = f"{secrets.randbelow(900000) + 100000}"
    salt = secrets.token_hex(16)
    _config = {
        "puerto": PUERTO,
        "salt": salt,
        "pin_hash": _hash_pin(pin, salt),
        "pin_plano": pin,
        "iters": PIN_ITERS,
        "stock_minimo": 5,
        "metodos_pago": list(METODOS),
        "creado": datetime.now().isoformat(timespec="seconds"),
    }
    guardar_config()
    return _config


def guardar_config() -> None:
    CONFIG_PATH.write_text(json.dumps(_config, indent=2, ensure_ascii=False), encoding="utf-8")


def pin_visible() -> str:
    return str(_config.get("pin_plano") or "")


def estado_actual() -> dict[str, Any]:
    cargar_config()
    umbral = int(_config.get("stock_minimo") or 5)
    data = leer_estado(umbral=umbral)
    data["metodos_pago"] = list(_config.get("metodos_pago") or METODOS)
    data["puede_vender"] = bool(data.get("caja") and data["caja"].get("abierta"))
    data["impresora"] = _printer_name() or None
    return data


async def publicar_estado() -> dict[str, Any]:
    global _ultima_firma
    estado = estado_actual()
    _ultima_firma = str(estado.get("firma") or "")
    muertos = []
    for cliente in list(_clientes_ws):
        try:
            await cliente.send_json(estado)
        except Exception:
            muertos.append(cliente)
    for cliente in muertos:
        _clientes_ws.discard(cliente)
    return estado


def ips_lan() -> list[str]:
    encontradas: list[str] = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            encontradas.append(sock.getsockname()[0])
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip not in encontradas and not ip.startswith("127."):
                encontradas.append(ip)
    except OSError:
        pass
    return [ip for ip in encontradas if not ip.startswith("127.")]


def url_panel() -> str:
    ips = ips_lan()
    host = ips[0] if ips else "127.0.0.1"
    return f"http://{host}:{PUERTO}"


def token_valido(token: str | None) -> bool:
    if not token:
        return False
    expira = _tokens.get(token)
    if not expira:
        return False
    if expira < time.time():
        _tokens.pop(token, None)
        return False
    return True


def exigir_token(authorization: str | None) -> None:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not token_valido(token):
        raise HTTPException(status_code=401, detail="Sesión inválida")


def _rate_limit(ip: str) -> None:
    ahora = time.time()
    ventana = [t for t in _intentos.get(ip, []) if ahora - t < 60]
    if len(ventana) >= 8:
        raise HTTPException(status_code=429, detail="Demasiados intentos. Espera un minuto.")
    ventana.append(ahora)
    _intentos[ip] = ventana


@app.get("/", response_class=HTMLResponse)
async def inicio() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/conexion", response_class=HTMLResponse)
async def conexion(request: Request) -> HTMLResponse:
    cargar_config()
    return templates.TemplateResponse(
        "conexion.html",
        {
            "request": request,
            "url": url_panel(),
            "urls": [f"http://{ip}:{PUERTO}" for ip in ips_lan()] or [f"http://127.0.0.1:{PUERTO}"],
            "pin": pin_visible(),
            "puerto": PUERTO,
            "nube": nube_activa(),
            "url_publica": url_publica(),
        },
    )


@app.get("/qr.svg")
async def qr_svg() -> Response:
    img = qrcode.make(
        url_panel(),
        image_factory=qrcode.image.svg.SvgPathImage,
        box_size=12,
        border=2,
    )
    buf = BytesIO()
    img.save(buf)
    return Response(content=buf.getvalue(), media_type="image/svg+xml")


@app.get("/api/salud")
async def salud() -> dict[str, Any]:
    return {
        "ok": True,
        "url": url_panel(),
        "nube": nube_activa(),
        "url_publica": url_publica() or None,
    }


@app.post("/api/login")
async def login(request: Request) -> JSONResponse:
    ip = request.client.host if request.client else "local"
    _rate_limit(ip)
    body = await request.json()
    pin = str(body.get("pin") or "").strip()
    esperado = _config.get("pin_hash", "")
    salt = _config.get("salt", "")
    recibido = _hash_pin(pin, salt)
    if not hmac.compare_digest(recibido, esperado):
        raise HTTPException(status_code=401, detail="PIN incorrecto")
    token = secrets.token_urlsafe(32)
    _tokens[token] = time.time() + 60 * 60 * 18
    return JSONResponse({"token": token, "expira_horas": 18})


@app.post("/api/vender")
async def vender(request: Request, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    exigir_token(authorization)
    body = await request.json()
    recibido = body.get("recibido")
    if recibido == "" or recibido is None:
        recibido = None
    else:
        try:
            recibido = float(recibido)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="El valor recibido no es válido.")
    try:
        resultado = await asyncio.to_thread(
            registrar_venta,
            body.get("items") or [],
            str(body.get("metodo_pago") or ""),
            recibido,
            str(body.get("nota") or ""),
            True,
        )
    except VentaError as exc:
        raise HTTPException(status_code=exc.codigo, detail=exc.mensaje) from exc
    await publicar_estado()
    resultado.pop("estado", None)
    return resultado


@app.get("/api/estado")
async def estado(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    exigir_token(authorization)
    try:
        return estado_actual()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.websocket("/ws")
async def websocket_panel(ws: WebSocket) -> None:
    token = ws.query_params.get("token")
    if not token_valido(token):
        await ws.close(code=4401)
        return
    await ws.accept()
    _clientes_ws.add(ws)
    try:
        await ws.send_json(estado_actual())
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        _clientes_ws.discard(ws)


async def bucle_vigilancia() -> None:
    global _ultima_firma
    while True:
        try:
            estado = estado_actual()
            firma = estado.get("firma")
            if firma and firma != _ultima_firma:
                _ultima_firma = str(firma)
                muertos = []
                for cliente in list(_clientes_ws):
                    try:
                        await cliente.send_json(estado)
                    except Exception:
                        muertos.append(cliente)
                for cliente in muertos:
                    _clientes_ws.discard(cliente)
        except Exception:
            pass
        await asyncio.sleep(0.8)


async def bucle_nube() -> None:
    while True:
        try:
            if nube_activa():
                msg = await asyncio.to_thread(ciclo_nube, estado_actual)
                if str(msg).startswith("pedidos"):
                    await publicar_estado()
        except Exception:
            pass
        await asyncio.sleep(1.5)


def imprimir_banner() -> None:
    cargar_config()
    url = url_panel()
    pin = pin_visible()
    lineas = [
        "",
        "  ============================================",
        "   CLUB BURGER  -  PANEL DEL DUENO",
        "  ============================================",
        "   Deja esta ventana abierta mientras atienden.",
        f"   En el celular:  {url}",
        f"   PIN:            {pin}",
        "   El celular en el WiFi del local usa esa direccion.",
        f"   Nube:           {'conectada' if nube_activa() else 'sin configurar (ver nube.env)'}",
        *([f"   Desde internet: {url_publica()}"] if url_publica() else []),
        "  ============================================",
        "",
    ]
    print("\n".join(lineas), flush=True)


if __name__ == "__main__":
    os.chdir(APP_ROOT)
    imprimir_banner()
    try:
        import webbrowser

        if os.environ.get("PANEL_NO_BROWSER") != "1":
            webbrowser.open(f"http://127.0.0.1:{PUERTO}/conexion")
    except Exception:
        pass
    uvicorn.run(app, host="0.0.0.0", port=PUERTO, log_level="warning")
