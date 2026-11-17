param(
  [Parameter(Mandatory = $true)]
  [ValidateSet('db-nuevo', 'migrar', 'seed', 'correr', 'probar', 'demo', 'lint')]
  [string]$Tarea,

  [string]$PgHost = 'localhost',
  [int]$Puerto = 5432,
  [string]$PgUser = 'postgres',
  [string]$PgPassword = 'admin',

  [string]$Base = 'vmp',
  [string]$BasePruebas = 'vmp_test',
  [string]$Url = 'http://127.0.0.1:8000'
)

$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent $PSScriptRoot
$python = Join-Path $raiz '.venv\Scripts\python.exe'
$psql = 'C:\Program Files\PostgreSQL\17\bin\psql.exe'

function Exigir-Python {
  if (-not (Test-Path $python)) {
    throw "No existe $python. Crea el entorno con: python -m venv .venv; .\.venv\Scripts\pip install -e `".[dev]`""
  }
}

switch ($Tarea) {
  'db-nuevo' {
    if (-not (Test-Path $psql)) { throw "No encuentro psql en $psql. Ajusta la ruta en este script." }
    $env:PGPASSWORD = $PgPassword
    foreach ($nombre in @($Base, $BasePruebas)) {
      $existe = & $psql -h $PgHost -p $Puerto -U $PgUser -w -t -A -c "SELECT 1 FROM pg_database WHERE datname='$nombre'"
      if ($existe -ne '1') {
        & $psql -h $PgHost -p $Puerto -U $PgUser -w -c "CREATE DATABASE $nombre ENCODING 'UTF8'"
        Write-Host "Base $nombre creada."
      } else {
        Write-Host "Base $nombre ya existe."
      }
    }
  }

  'migrar' {
    Exigir-Python
    Push-Location $raiz
    try { & $python -m alembic upgrade head } finally { Pop-Location }
  }

  'seed' {
    Exigir-Python
    Push-Location $raiz
    try { & $python -m app.seed } finally { Pop-Location }
  }

  'correr' {
    Exigir-Python
    Push-Location $raiz
    try { & $python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 } finally { Pop-Location }
  }

  'probar' {
    Exigir-Python
    Push-Location $raiz
    try { & $python -m pytest -q } finally { Pop-Location }
  }

  'lint' {
    Exigir-Python
    Push-Location $raiz
    try {
      & $python -m ruff check app tests alembic
      & $python -m ruff format --check app tests alembic
    } finally { Pop-Location }
  }

  'demo' {
    Exigir-Python
    Push-Location $raiz
    try { & $python scripts\demo_flujo.py --url $Url } finally { Pop-Location }
  }
}
