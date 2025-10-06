param(
    [string]$ApiBase = "http://127.0.0.1:8000",
    [string]$SoapUrl = "http://127.0.0.1:9000/",
    [string]$Username = $("userprueba_" + [System.Guid]::NewGuid().ToString("N").Substring(0, 8)),
    [string]$Email = $("userprueba_" + [System.Guid]::NewGuid().ToString("N").Substring(0, 8) + "@example.com"),
    [string]$Password = "Secret123",
    [string]$ImagePath = "..\img\imagen.jpg",
    [string]$OutputFormat = "png",
    [string]$TransformsJson = '[{"code":"grayscale"},{"code":"resize","params":{"width":256,"height":256}}]'
)

<#!
.SYNOPSIS
    Ejecuta el flujo completo: registro, login y solicitud de transformación de imagen.
.DESCRIPTION
    - Registra un usuario nuevo usando /signup
    - Inicia sesión con /login
    - Envía una imagen a /procesar-imagen y muestra la respuesta
.NOTES
    Ejecutar desde la raíz del proyecto (distribuidos-img) con los servicios levantados.
    Ejemplo:
        pwsh -File .\scripts\run_end_to_end.ps1 -Password "TuClaveSegura1!"
#>

function Invoke-JsonPost {
    param(
        [Parameter(Mandatory)][string]$Url,
        [Parameter(Mandatory)][hashtable]$Body
    )

    $json = $Body | ConvertTo-Json -Depth 5
    try {
        return Invoke-RestMethod -Uri $Url -Method POST -Body $json -ContentType "application/json"
    }
    catch {
        Write-Error ("Error al llamar {0}: {1}" -f $Url, $_.Exception.Message)
        throw
    }
}

function Get-ResolvedImagePath {
    param([string]$Path)
    try {
        return (Resolve-Path $Path -ErrorAction Stop).Path
    }
    catch {
        throw "No se pudo resolver la ruta del archivo de entrada: $Path"
    }
}

function Invoke-ImageTransform {
    param(
        [int]$UsuarioId,
        [string]$ResolvedImagePath,
        [string]$OutputFormat,
        [string]$TransformsJson,
        [string]$ApiBase
    )

    Add-Type -AssemblyName System.Net.Http
    $client  = [System.Net.Http.HttpClient]::new()
    $content = [System.Net.Http.MultipartFormDataContent]::new()

    try {
        $content.Add([System.Net.Http.StringContent]::new($UsuarioId.ToString()), "usuario_id")
        $content.Add([System.Net.Http.StringContent]::new($OutputFormat), "output_format")
        $content.Add([System.Net.Http.StringContent]::new($TransformsJson), "transforms")

        $fileStream  = [System.IO.File]::OpenRead($ResolvedImagePath)
        try {
            $fileContent = [System.Net.Http.StreamContent]::new($fileStream)
            $fileContent.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse("image/jpeg")
            $fileName = [System.IO.Path]::GetFileName($ResolvedImagePath)
            $content.Add($fileContent, "file", $fileName)

            $endpoint = "$ApiBase/procesar-imagen"
            $response = $client.PostAsync($endpoint, $content).Result
            $body     = $response.Content.ReadAsStringAsync().Result

            if ($response.IsSuccessStatusCode) {
                return $body | ConvertFrom-Json
            }
            else {
                throw "Solicitud HTTP falló ($($response.StatusCode)): $body"
            }
        }
        finally {
            $fileStream.Dispose()
        }
    }
    finally {
        $client.Dispose()
    }
}

Write-Host "--- Flujo end-to-end ---" -ForegroundColor Cyan
Write-Host "SOAP URL: $SoapUrl" -ForegroundColor DarkGray
Write-Host "API REST: $ApiBase" -ForegroundColor DarkGray

# 1. Registro
Write-Host "[1/3] Registrando usuario $Username..." -ForegroundColor Cyan
$signupBody = @{ username = $Username; email = $Email; password = $Password }
$signupResp = Invoke-JsonPost -Url "$ApiBase/signup" -Body $signupBody
$usuarioId  = $signupResp.usuario_id
Write-Host "    Usuario registrado con ID $usuarioId" -ForegroundColor Green

# 2. Login
Write-Host "[2/3] Iniciando sesión..." -ForegroundColor Cyan
$loginBody = @{ username = $Username; password = $Password }
$loginResp = Invoke-JsonPost -Url "$ApiBase/login" -Body $loginBody
$usuarioId = $loginResp.usuario_id
Write-Host "    Sesión iniciada para $($loginResp.username) (ID $usuarioId)" -ForegroundColor Green

# 3. Transformación
Write-Host "[3/3] Solicitando transformación..." -ForegroundColor Cyan
$resolvedImage = Get-ResolvedImagePath -Path $ImagePath
$result = Invoke-ImageTransform -UsuarioId $usuarioId -ResolvedImagePath $resolvedImage -OutputFormat $OutputFormat -TransformsJson $TransformsJson -ApiBase $ApiBase
Write-Host "    Transformación enviada. Respuesta:" -ForegroundColor Green
$result | ConvertTo-Json -Depth 6 | Write-Host

if ($result.solicitud.solicitud_id) {
    $solId = $result.solicitud.solicitud_id
    $outputDir = Join-Path -Path "data\output" -ChildPath $solId
    Write-Host "Archivos de salida esperados en: $outputDir" -ForegroundColor Yellow
}

Write-Host "Flujo completado." -ForegroundColor Cyan
