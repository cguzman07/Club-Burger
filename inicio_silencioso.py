"""Arranca el panel en segundo plano (sin terminal) y abre el POS."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

CREATE_NO_WINDOW = 0x08000000
ROOT = Path(__file__).resolve().parent
PANEL = ROOT / "panel_dueno"
VENV_PY = PANEL / ".venv" / "Scripts" / "python.exe"
VENV_PYW = PANEL / ".venv" / "Scripts" / "pythonw.exe"
SERVER = PANEL / "server.py"
REQ = PANEL / "requirements.txt"
LOG = PANEL / "panel.log"
PUERTO = int(os.environ.get("PANEL_PUERTO", "5050"))


def _log(mensaje: str) -> None:
    try:
        PANEL.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat(timespec='seconds')} {mensaje}\n")
    except OSError:
        pass


def _sin_ventana() -> int:
    return CREATE_NO_WINDOW if os.name == "nt" else 0


def _puerto_ocupado(puerto: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.25)
        return s.connect_ex(("127.0.0.1", puerto)) == 0


def _py_sistema() -> list[str]:
    py = shutil.which("py")
    if py:
        return [py, "-3"]
    python = shutil.which("python")
    if python:
        return [python]
    raise RuntimeError("No se encontró Python en este computador.")


def _run(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        cwd=str(ROOT),
        creationflags=_sin_ventana(),
        **kwargs,
    )


def _venv_sirve() -> bool:
    if not VENV_PYW.exists() or not VENV_PY.exists():
        return False
    cfg = PANEL / ".venv" / "pyvenv.cfg"
    if cfg.exists():
        for linea in cfg.read_text(encoding="utf-8", errors="replace").splitlines():
            if linea.lower().startswith("home"):
                home = Path(linea.split("=", 1)[-1].strip())
                if not (home / "python.exe").exists() and not (home / "pythonw.exe").exists():
                    return False
    prueba = _run([str(VENV_PY), "-c", "import sys"], capture_output=True)
    return prueba.returncode == 0


def _preparar_venv() -> Path:
    if _venv_sirve():
        return VENV_PYW
    destino = PANEL / ".venv"
    if destino.exists():
        _log("El entorno copiado de otro PC no sirve; se recrea")
        shutil.rmtree(destino, ignore_errors=True)
    _log("Creando entorno del panel")
    _run(_py_sistema() + ["-m", "venv", str(destino)], check=True)
    pip = [str(VENV_PY), "-m", "pip", "install", "-q", "-r", str(REQ)]
    _run(pip, check=True)
    if not VENV_PYW.exists():
        raise RuntimeError("No se pudo crear pythonw para el panel.")
    return VENV_PYW


def _firewall() -> None:
    try:
        r = _run(
            ["netsh", "advfirewall", "firewall", "show", "rule", "name=Club Burger Panel Dueño"],
            capture_output=True,
        )
        if r.returncode != 0:
            _run(
                [
                    "netsh",
                    "advfirewall",
                    "firewall",
                    "add",
                    "rule",
                    "name=Club Burger Panel Dueño",
                    "dir=in",
                    "action=allow",
                    "protocol=TCP",
                    "localport=5050",
                ],
                capture_output=True,
            )
    except OSError:
        pass


def _arrancar_panel() -> None:
    if _puerto_ocupado(PUERTO):
        _log(f"Panel ya está en el puerto {PUERTO}")
        return
    pyw = _preparar_venv()
    _firewall()
    env = os.environ.copy()
    env["PANEL_NO_BROWSER"] = "1"
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    subprocess.Popen(
        [str(pyw), str(SERVER)],
        cwd=str(ROOT),
        env=env,
        creationflags=_sin_ventana(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(25):
        if _puerto_ocupado(PUERTO):
            _log("Panel iniciado")
            return
        time.sleep(0.2)
    _log("El panel no respondió a tiempo")


def _exe_pos() -> Path | None:
    for nombre in ("ClubBurgerPOS.exe", "Club Burger POS.exe"):
        candidato = ROOT / nombre
        if candidato.exists():
            return candidato
    candidato = ROOT / "Club Burger.exe"
    if candidato.exists() and candidato.stat().st_size > 1_000_000:
        return candidato
    return None


def _arrancar_pos() -> None:
    exe = _exe_pos()
    if exe is None:
        _log("No se encontró el POS")
        return
    subprocess.Popen([str(exe)], cwd=str(ROOT))
    _log(f"POS iniciado: {exe.name}")


def main() -> int:
    solo_panel = "--solo-panel" in sys.argv
    try:
        _arrancar_panel()
        if not solo_panel:
            _arrancar_pos()
        return 0
    except Exception as exc:
        _log(f"ERROR {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
