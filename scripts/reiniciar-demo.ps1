<#
.SYNOPSIS
  Deja la demo en cero: borra todos los datos y vuelve a levantar el sistema.

.DESCRIPTION
  Borra los vehiculos, fotos e ingresos de la demo y vuelve a crear los datos
  base: los mismos 6 perfiles UTP y 3 guardias (para iniciar sesion) y 40
  espacios libres. Por defecto los perfiles empiezan SIN vehiculos, para
  registrarlos con su foto real frente a la camara (docs/27).

  No toca la base de pruebas (vmp-test-db) ni los pesos del modelo.

.EXAMPLE
  .\scripts\reiniciar-demo.ps1
  .\scripts\reiniciar-demo.ps1 -ConEjemplos   # perfiles con vehiculos de ejemplo (fotos dibujadas)
  .\scripts\reiniciar-demo.ps1 -SinIA         # sin el detector real (usa el doble)
#>
param(
    [switch]$ConEjemplos,
    [switch]$SinIA,
    [switch]$SinConfirmar
)

$raiz = Split-Path $PSScriptRoot -Parent
Set-Location $raiz

function Detener([string]$mensaje) {
    Write-Host "ERROR: $mensaje" -ForegroundColor Red
    exit 1
}

docker info *> $null
if ($LASTEXITCODE -ne 0) { Detener 'Docker Desktop no esta abierto. Abrelo y espera a que diga "Engine running".' }

if (-not $SinIA -and -not (Test-Path 'ia_service/pesos/E2-3clases-best.pt')) {
    Detener 'Faltan los pesos ia_service/pesos/E2-3clases-best.pt (ver ia_service/pesos/LEEME.md), o usa -SinIA.'
}

if (-not $SinConfirmar) {
    Write-Host 'Se borraran los vehiculos, fotos e ingresos, y los 40 espacios quedaran libres.' -ForegroundColor Yellow
    Write-Host 'Los 6 perfiles UTP y los 3 guardias se mantienen: podras iniciar sesion igual.' -ForegroundColor Yellow
    $respuesta = Read-Host 'Escribe SI para continuar'
    if ($respuesta -ne 'SI') { Write-Host 'Cancelado. No se borro nada.'; exit 0 }
}

if (-not $env:DB_PUERTO) { $env:DB_PUERTO = '55433' }   # el PostgreSQL local ocupa el 5432
$env:SEED_VEHICULOS = if ($ConEjemplos) { '1' } else { '0' }
$perfiles = @()
if ($SinIA) { $env:IA_MODO = 'stub' } else { $env:IA_MODO = 'http'; $perfiles = @('--profile', 'ia') }

Write-Host '1/3 Borrando datos...' -ForegroundColor Cyan
docker compose --profile ia down -v
if ($LASTEXITCODE -ne 0) { Detener 'No se pudo apagar el sistema.' }

Write-Host '2/3 Levantando el sistema (la primera vez tarda varios minutos)...' -ForegroundColor Cyan
docker compose @perfiles up -d --build
if ($LASTEXITCODE -ne 0) { Detener 'No se pudo levantar el sistema. Revisa: docker compose logs backend' }

Write-Host '3/3 Esperando al backend y a la IA...' -ForegroundColor Cyan
$salud = $null
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 3
    $texto = curl.exe -s -m 30 http://localhost:8000/salud
    if ($LASTEXITCODE -eq 0 -and $texto) {
        try { $salud = $texto | ConvertFrom-Json } catch { $salud = $null }
        if ($salud -and $salud.base_datos -eq 'ok' -and $salud.ia.disponible) { break }
    }
}
if (-not $salud) { Detener 'El backend no respondio en 3 minutos. Revisa: docker compose logs backend' }

$token = (curl.exe -s -X POST http://localhost:8000/api/v1/dev/sesion/guardia/guardia.tarde | ConvertFrom-Json).access_token
$espacios = curl.exe -s -H "Authorization: Bearer $token" http://localhost:8000/api/v1/espacios | ConvertFrom-Json
$identidades = curl.exe -s http://localhost:8000/api/v1/dev/identidades | ConvertFrom-Json

Write-Host ''
Write-Host 'Listo. Datos de la demo en cero.' -ForegroundColor Green
Write-Host ("  Base de datos : {0}" -f $salud.base_datos)
Write-Host ("  IA            : {0} ({1})" -f $(if ($salud.ia.disponible) { 'disponible' } else { 'NO disponible' }), $salud.ia.modelo_version)
Write-Host ("  Espacios      : {0} de {1} libres" -f $espacios.libres, $espacios.total)
Write-Host ("  Vehiculos     : {0}" -f $(if ($ConEjemplos) { 'con ejemplos (fotos dibujadas)' } else { 'ninguno: se registran en el Portal' }))
Write-Host '  Perfiles      :'
foreach ($u in $identidades.usuarios) { Write-Host ("     {0}  {1} {2}" -f $u.codigo_utp, $u.nombres, $u.apellidos) }
Write-Host '  Guardias      :'
foreach ($g in $identidades.guardia) { Write-Host ("     {0}  {1} {2}" -f $g.usuario_acceso, $g.nombres, $g.apellidos) }
Write-Host ''
Write-Host '  Portal  http://localhost:5173/portal'
Write-Host '  App     http://localhost:5173/app   (celular: http://<IP de la laptop>:5173/app)'
Write-Host '  Guardia http://localhost:5173/acceso   y   http://localhost:5173/espacios'
