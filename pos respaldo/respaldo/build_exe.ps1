# Construye ClubBurgerPOS.exe (carpeta dist\ClubBurgerPOS)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $Root

$Py = "C:\Python314\python.exe"
if (-not (Test-Path $Py)) {
    $Py = (Get-Command py -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)
    if ($Py) { $Py = "py"; $PyArgs = @("-3") } else { throw "No se encontro Python 3." }
} else {
    $PyArgs = @()
}

$env:TCL_LIBRARY = "C:\Users\Crhistian\AppData\Local\Programs\Python\Python314\tcl\tcl8.6"
$env:TK_LIBRARY  = "C:\Users\Crhistian\AppData\Local\Programs\Python\Python314\tcl\tk8.6"

Write-Host "==> Instalando dependencias de build..."
& $Py @PyArgs -m pip install --upgrade pip
& $Py @PyArgs -m pip install -r requirements.txt pyinstaller

if (-not (Test-Path "assets\club_burger.ico")) {
    throw "Falta assets\club_burger.ico - regenera el icono antes de empaquetar."
}

Write-Host "==> Limpiando build anterior..."
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue build, "dist\Club Burger", "dist\ClubBurgerPOS"

Write-Host "==> PyInstaller..."
& $Py @PyArgs -m PyInstaller --noconfirm --clean ClubBurgerPOS.spec

$Dist = Join-Path $Root "dist\Club Burger"
if (-not (Test-Path (Join-Path $Dist "Club Burger.exe"))) {
    throw "No se genero el ejecutable."
}

# Datos de trabajo junto al .exe (BD, factura)
Copy-Item -Force "datos_pos.db" $Dist -ErrorAction SilentlyContinue
if (Test-Path "numero_factura.txt") {
    Copy-Item -Force "numero_factura.txt" $Dist
}
if (Test-Path "logo.bmp.png") {
    Copy-Item -Force "logo.bmp.png" $Dist
}

Write-Host ""
Write-Host "Listo:"
Write-Host "  $Dist\Club Burger.exe"
Write-Host ""
Write-Host "Copia toda la carpeta dist\Club Burger al equipo de venta."
Write-Host "Mantener datos_pos.db y logo.bmp.png junto al .exe (como en el local)."
