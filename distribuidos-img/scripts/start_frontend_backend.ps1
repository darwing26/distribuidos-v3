# Script para iniciar TODOS los servicios (Frontend + Backend + SOAP + Worker)
Write-Host "`n=== INICIANDO ARQUITECTURA COMPLETA ===" -ForegroundColor Cyan
Write-Host "Frontend → Backend → SOAP → Workers`n" -ForegroundColor DarkGray

# Limpiar procesos antiguos
Write-Host "[1] Limpiando procesos antiguos..." -ForegroundColor Yellow
Stop-Process -Name python -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

$projectDir = "C:\Users\knene\OneDrive\Desktop\distribuidos v3\distribuidos-img"
cd $projectDir

# Iniciar Worker gRPC
Write-Host "[2] Iniciando Worker gRPC (puerto 50051)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
cd '$projectDir'
.\.venv311\Scripts\Activate.ps1
Write-Host '🟢 WORKER gRPC - Puerto 50051' -ForegroundColor Green
python nodes/worker/server.py
"@
Start-Sleep -Seconds 3

# Iniciar Servidor SOAP
Write-Host "[3] Iniciando Servidor SOAP (puerto 9000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
cd '$projectDir'
.\.venv311\Scripts\Activate.ps1
Write-Host '🟢 SOAP Service - Puerto 9000' -ForegroundColor Green
python -m backend.soap_service
"@
Start-Sleep -Seconds 3

# Iniciar Backend API
Write-Host "[4] Iniciando Backend API (puerto 8000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
cd '$projectDir'
.\.venv311\Scripts\Activate.ps1
Write-Host '🟢 BACKEND API - Puerto 8000' -ForegroundColor Green
uvicorn backend.api:app --host 127.0.0.1 --port 8000
"@
Start-Sleep -Seconds 3

# Iniciar Frontend API
Write-Host "[5] Iniciando Frontend API (puerto 3000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
cd '$projectDir'
.\.venv311\Scripts\Activate.ps1
Write-Host '🟢 FRONTEND API - Puerto 3000' -ForegroundColor Cyan
python frontend/app.py
"@
Start-Sleep -Seconds 3

# Verificar que todos están corriendo
Write-Host "`n[6] Verificando servicios..." -ForegroundColor Yellow
$ports = @(
    @{Port=50051; Name="Worker gRPC"},
    @{Port=9000; Name="SOAP"},
    @{Port=8000; Name="Backend API"},
    @{Port=3000; Name="Frontend API"}
)

foreach ($service in $ports) {
    $listening = netstat -ano | findstr ":$($service.Port)" | findstr "LISTENING"
    if ($listening) {
        Write-Host "   ✅ $($service.Name) (puerto $($service.Port)) ACTIVO" -ForegroundColor Green
    } else {
        Write-Host "   ❌ $($service.Name) (puerto $($service.Port)) NO DISPONIBLE" -ForegroundColor Red
    }
}

Write-Host "`n=== ARQUITECTURA INICIADA ===" -ForegroundColor Cyan
Write-Host @"

📍 ARQUITECTURA COMPLETA:
┌─────────────────────────────────────────┐
│ Cliente (test_frontend.py)              │
└─────────────────┬───────────────────────┘
                  │ HTTP REST
┌─────────────────▼───────────────────────┐
│ Frontend API (puerto 3000)              │
└─────────────────┬───────────────────────┘
                  │ HTTP REST
┌─────────────────▼───────────────────────┐
│ Backend API (puerto 8000)               │
└─────────────────┬───────────────────────┘
                  │ SOAP
┌─────────────────▼───────────────────────┐
│ SOAP Service (puerto 9000)              │
└─────────────────┬───────────────────────┘
                  │ gRPC (Round-Robin)
┌─────────────────▼───────────────────────┐
│ Workers (puerto 50051+)                 │
└─────────────────────────────────────────┘

"@ -ForegroundColor DarkGray

Write-Host "Presiona cualquier tecla para ejecutar el test..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Ejecutar test
Write-Host "`nEjecutando test_frontend.py...`n" -ForegroundColor Cyan
python test_frontend.py
