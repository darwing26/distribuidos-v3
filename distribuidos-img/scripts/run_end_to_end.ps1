param(
    [string]$ApiBase = "http://127.0.0.1:8000",
    [string]$SoapUrl = "http://127.0.0.1:9000/",
    [string]$Username = $("userprueba_" + [System.Guid]::NewGuid().ToString("N").Substring(0, 8)),
    [string]$Email = $("userprueba_" + [System.Guid]::NewGuid().ToString("N").Substring(0, 8) + "@example.com"),
    [string]$Password = "Secret123",
    [string[]]$ImagePaths = @("..\img\imagen1.png","..\img\imagen2.png","..\img\imagen3.png","..\img\imagen4.png","..\img\imagen5.png","..\img\imagen6.png","..\img\imagen7.png","..\img\imagen8.png","..\img\imagen9.png","..\img\imagen10.png","..\img\imagen11.png","..\img\imagen12.png","..\img\imagen13.png","..\img\imagen14.png","..\img\imagen15.png","..\img\imagen16.png","..\img\imagen17.png","..\img\imagen18.png","..\img\imagen19.png","..\img\imagen20.png","..\img\imagen21.png","..\img\imagen22.png","..\img\imagen23.png","..\img\imagen24.png","..\img\imagen25.png","..\img\imagen26.png","..\img\imagen27.png","..\img\imagen28.png","..\img\imagen29.png","..\img\imagen30.png","..\img\imagen31.png","..\img\imagen32.png","..\img\imagen33.png","..\img\imagen34.png","..\img\imagen35.png","..\img\imagen36.png","..\img\imagen37.png"
),
    [string]$OutputFormat = "jpg",
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

function Get-ResolvedImagePaths {
    param([string[]]$Paths)
    $resolved = @()
    foreach ($path in $Paths) {
        try {
            $resolved += (Resolve-Path $path -ErrorAction Stop).Path
        }
        catch {
            throw "No se pudo resolver la ruta del archivo de entrada: $path"
        }
    }
    return $resolved
}

function Invoke-ImageBatch {
    param(
        [int]$UsuarioId,
        [string[]]$ResolvedImagePaths,
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

        $streams = @()
        try {
            foreach ($path in $ResolvedImagePaths) {
                $stream = [System.IO.File]::OpenRead($path)
                $streams += $stream
                $fileContent = [System.Net.Http.StreamContent]::new($stream)
                $ext = [System.IO.Path]::GetExtension($path)
                $mime = "application/octet-stream"
                switch ($ext.ToLowerInvariant()) {
                    ".jpg" { $mime = "image/jpeg" }
                    ".jpeg" { $mime = "image/jpeg" }
                    ".png" { $mime = "image/png" }
                    ".bmp" { $mime = "image/bmp" }
                    ".gif" { $mime = "image/gif" }
                    default { }
                }
                $fileContent.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse($mime)
                $fileName = [System.IO.Path]::GetFileName($path)
                $content.Add($fileContent, "files", $fileName)
            }

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
            foreach ($s in $streams) {
                $s.Dispose()
            }
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
$resolvedImages = Get-ResolvedImagePaths -Paths $ImagePaths
Write-Host "    Enviando $($resolvedImages.Count) archivo(s)" -ForegroundColor DarkGray
$result = Invoke-ImageBatch -UsuarioId $usuarioId -ResolvedImagePaths $resolvedImages -OutputFormat $OutputFormat -TransformsJson $TransformsJson -ApiBase $ApiBase
Write-Host "    Transformación enviada. Respuesta:" -ForegroundColor Green
$result | ConvertTo-Json -Depth 6 | Write-Host

if ($result.solicitud.solicitud_id) {
    $solId = $result.solicitud.solicitud_id
    $outputDir = Join-Path -Path "data\output" -ChildPath $solId
    Write-Host "Archivos de salida esperados en: $outputDir" -ForegroundColor Yellow
}

Write-Host "Flujo completado." -ForegroundColor Cyan
