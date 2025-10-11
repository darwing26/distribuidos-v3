# Script maestro para iniciar todos los servicios
Write-Host "=== Iniciando Sistema Distribuido ===" -ForegroundColor Cyan

# Limpiar terminales antiguas
Write-Host "[1] Limpiando procesos antiguos..." -ForegroundColor Yellow
Stop-Process -Name python -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Cambiar al directorio del proyecto
$projectDir = "C:\Users\knene\OneDrive\Desktop\distribuidos v3\distribuidos-img"
cd $projectDir

# Activar entorno virtual
.\.venv311\Scripts\Activate.ps1

# Iniciar Worker gRPC
Write-Host "[2] Iniciando Worker gRPC en puerto 50051..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectDir'; .\.venv311\Scripts\Activate.ps1; python nodes/worker/server.py"
Start-Sleep -Seconds 3

# Iniciar Servidor SOAP
Write-Host "[3] Iniciando Servidor SOAP en puerto 9000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectDir'; .\.venv311\Scripts\Activate.ps1; python -m backend.soap_service"
Start-Sleep -Seconds 3

# Iniciar API FastAPI
Write-Host "[4] Iniciando API FastAPI en puerto 8000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectDir'; .\.venv311\Scripts\Activate.ps1; uvicorn backend.api:app --host 127.0.0.1 --port 8000"
Start-Sleep -Seconds 3

# Verificar que todos están corriendo
Write-Host "`n[5] Verificando servicios..." -ForegroundColor Yellow
$ports = @(50051, 9000, 8000)
foreach ($port in $ports) {
    $listening = netstat -ano | findstr ":$port" | findstr "LISTENING"
    if ($listening) {
        Write-Host "   ✅ Puerto $port ACTIVO" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Puerto $port NO DISPONIBLE" -ForegroundColor Red
    }
}

Write-Host "`n=== Sistema Iniciado ===" -ForegroundColor Cyan
Write-Host "Presiona cualquier tecla para ejecutar el test..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Ejecutar test
cd scripts
.\test_batch_processing.ps1
