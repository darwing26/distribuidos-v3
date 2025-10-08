param(
    [string]$ApiBase = "http://127.0.0.1:8000",
    [string]$Username = $("user_" + [System.Guid]::NewGuid().ToString("N").Substring(0, 8)),
    [string]$Email = $("user_" + [System.Guid]::NewGuid().ToString("N").Substring(0, 8) + "@example.com"),
    [string]$Password = "SecurePass123",
    [string[]]$ImagePaths = @(),
    [string]$OutputFormat = "jpg"
)

<#
.SYNOPSIS
    Script de prueba para procesamiento en lote de imágenes con transformaciones.

.DESCRIPTION
    Este script demuestra cómo:
    1. Registrar un usuario
    2. Iniciar sesión
    3. Enviar múltiples imágenes con hasta 5 transformaciones cada una
    4. Recibir un archivo ZIP con todas las imágenes procesadas

.EXAMPLE
    .\test_batch_processing.ps1 -ImagePaths @("imagen1.jpg","imagen2.png")
#>

function Invoke-JsonPost {
    param(
        [Parameter(Mandatory)][string]$Url,
        [Parameter(Mandatory)][hashtable]$Body
    )
    $json = $Body | ConvertTo-Json -Depth 10
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

    $hasProvidedPaths = $Paths -and ($Paths | Where-Object { $_ -and $_.Trim() -ne "" }).Count -gt 0

    if (-not $hasProvidedPaths) {
        Write-Host "      Buscando imágenes en carpetas conocidas..." -ForegroundColor DarkGray

        $candidateDirs = @(
            (Join-Path $PSScriptRoot "..\img"),
            (Join-Path (Split-Path $PSScriptRoot -Parent) "img"),
            (Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) "img"),
            (Join-Path (Get-Location) "img")
        ) | Select-Object -Unique

        foreach ($dir in $candidateDirs) {
            if (-not (Test-Path $dir)) { continue }

            $found = Get-ChildItem -Path "$dir\*" -Include *.jpg,*.jpeg,*.png,*.bmp,*.gif,*.tif,*.tiff -File |
                Select-Object -First 5

            if ($found -and $found.Count -gt 0) {
                $resolved = $found | ForEach-Object { $_.FullName }
                Write-Host "      Encontradas $($resolved.Count) imagen(es) en $dir" -ForegroundColor Green
                break
            }
        }

        if ($resolved.Count -eq 0) {
            throw "No se encontraron imágenes. Usa el parámetro -ImagePaths o coloca archivos en la carpeta 'img'."
        }

        return $resolved
    }

    foreach ($path in $Paths) {
        if (-not $path) { continue }

        $attempts = @($path)
        if (-not [System.IO.Path]::IsPathRooted($path)) {
            $attempts += (Join-Path $PSScriptRoot $path)
            $attempts += (Join-Path (Split-Path $PSScriptRoot -Parent) $path)
            $attempts += (Join-Path (Get-Location) $path)
        }

        $resolvedPath = $null
        foreach ($candidate in $attempts | Select-Object -Unique) {
            try {
                $candidatePath = Resolve-Path $candidate -ErrorAction Stop
                if ($candidatePath) {
                    $resolvedPath = $candidatePath.Path
                    break
                }
            }
            catch {
                continue
            }
        }

        if ($resolvedPath) {
            $resolved += $resolvedPath
        }
        else {
            Write-Warning "No se pudo resolver la ruta: $path"
        }
    }

    if ($resolved.Count -eq 0) {
        throw "No se pudo resolver ninguna ruta de imagen válida."
    }

    return $resolved
}

Write-Host "`n=== PRUEBA DE PROCESAMIENTO EN LOTE ===" -ForegroundColor Cyan
Write-Host "API: $ApiBase`n" -ForegroundColor DarkGray

# 1. Registro
Write-Host "[1/4] Registrando usuario..." -ForegroundColor Yellow
$signupBody = @{ username = $Username; email = $Email; password = $Password }
$signupResp = Invoke-JsonPost -Url "$ApiBase/signup" -Body $signupBody
$usuarioId = $signupResp.usuario_id
Write-Host "      Usuario registrado: $Username (ID: $usuarioId)" -ForegroundColor Green

# 2. Login
Write-Host "[2/4] Iniciando sesión..." -ForegroundColor Yellow
$loginBody = @{ username = $Username; password = $Password }
$loginResp = Invoke-JsonPost -Url "$ApiBase/login" -Body $loginBody
Write-Host "      Sesión iniciada" -ForegroundColor Green

# 3. Preparar instrucciones de transformación por imagen
Write-Host "[3/4] Preparando transformaciones..." -ForegroundColor Yellow

$resolvedImages = Get-ResolvedImagePaths -Paths $ImagePaths
Write-Host "      Procesando $($resolvedImages.Count) imagen(es)" -ForegroundColor DarkGray

foreach ($img in $resolvedImages) {
    Write-Host "        • $(Split-Path $img -Leaf)" -ForegroundColor DarkGray
}

# Crear instrucciones específicas para cada imagen
$instructions = @()

# Imagen 1: Escala de grises + Redimensionar + Rotar
$instructions += @{
    filename = [System.IO.Path]::GetFileName($resolvedImages[0])
    output_format = "jpg"
    transforms = @(
        @{ code = "GRAYSCALE"; order = 1 },
        @{ code = "RESIZE"; params = @{ width = 800; height = 600 }; order = 2 },
        @{ code = "ROTATE"; params = @{ degrees = 90 }; order = 3 }
    )
}

# Imagen 2: Desenfocar + Marca de agua + Ajustar brillo
if ($resolvedImages.Count -gt 1) {
    $instructions += @{
        filename = [System.IO.Path]::GetFileName($resolvedImages[1])
        output_format = "png"
        transforms = @(
            @{ code = "BLUR"; params = @{ radius = 3.0 }; order = 1 },
            @{ code = "WATERMARK"; params = @{ text = "Procesado"; x = 20; y = 20 }; order = 2 },
            @{ code = "BRIGHTNESS_CONTRAST"; params = @{ brightness = 1.2; contrast = 1.1 }; order = 3 }
        )
    }
}

# Imagen 3: Recortar + Reflejar + Perfilar
if ($resolvedImages.Count -gt 2) {
    $instructions += @{
        filename = [System.IO.Path]::GetFileName($resolvedImages[2])
        output_format = "tif"
        transforms = @(
            @{ code = "CROP"; params = @{ x = 100; y = 100; width = 500; height = 500 }; order = 1 },
            @{ code = "FLIP"; params = @{ axis = "horizontal" }; order = 2 },
            @{ code = "SHARPEN"; params = @{ factor = 2.0 }; order = 3 }
        )
    }
}

$instructionsJson = $instructions | ConvertTo-Json -Depth 10 -Compress
Write-Host "      Instrucciones preparadas" -ForegroundColor Green

# 4. Enviar solicitud
Write-Host "[4/4] Enviando solicitud de procesamiento..." -ForegroundColor Yellow

Add-Type -AssemblyName System.Net.Http
$client = [System.Net.Http.HttpClient]::new()
$content = [System.Net.Http.MultipartFormDataContent]::new()

try {
    # Agregar parámetros
    $content.Add([System.Net.Http.StringContent]::new($usuarioId.ToString()), "usuario_id")
    $content.Add([System.Net.Http.StringContent]::new($OutputFormat), "output_format")
    $content.Add([System.Net.Http.StringContent]::new($instructionsJson), "instructions")

    # Agregar archivos
    $streams = @()
    try {
        foreach ($path in $resolvedImages) {
            $stream = [System.IO.File]::OpenRead($path)
            $streams += $stream
            $fileContent = [System.Net.Http.StreamContent]::new($stream)
            
            $ext = [System.IO.Path]::GetExtension($path)
            $mime = switch ($ext.ToLowerInvariant()) {
                ".jpg" { "image/jpeg" }
                ".jpeg" { "image/jpeg" }
                ".png" { "image/png" }
                ".bmp" { "image/bmp" }
                ".gif" { "image/gif" }
                ".tif" { "image/tiff" }
                ".tiff" { "image/tiff" }
                default { "application/octet-stream" }
            }
            $fileContent.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse($mime)
            $fileName = [System.IO.Path]::GetFileName($path)
            $content.Add($fileContent, "files", $fileName)
        }

        $endpoint = "$ApiBase/procesar-imagen"
        Write-Host "      Esperando respuesta..." -ForegroundColor DarkGray
        
        $response = $client.PostAsync($endpoint, $content).Result
        
        if ($response.IsSuccessStatusCode) {
            # Guardar el archivo ZIP
            $zipContent = $response.Content.ReadAsByteArrayAsync().Result
            $outputPath = "imagenes_procesadas_" + [DateTime]::Now.ToString("yyyyMMdd_HHmmss") + ".zip"
            [System.IO.File]::WriteAllBytes($outputPath, $zipContent)
            
            Write-Host "`n=== ÉXITO ===" -ForegroundColor Green
            Write-Host "Archivo ZIP creado: $outputPath" -ForegroundColor Cyan
            Write-Host "Tamaño: $([Math]::Round($zipContent.Length / 1024, 2)) KB" -ForegroundColor DarkGray
            
            # Mostrar contenido del ZIP
            Write-Host "`nContenido del ZIP:" -ForegroundColor Yellow
            Add-Type -AssemblyName System.IO.Compression.FileSystem
            $zip = [System.IO.Compression.ZipFile]::OpenRead($outputPath)
            foreach ($entry in $zip.Entries) {
                Write-Host "  - $($entry.Name) ($([Math]::Round($entry.Length / 1024, 2)) KB)" -ForegroundColor White
            }
            $zip.Dispose()
        }
        else {
            $body = $response.Content.ReadAsStringAsync().Result
            Write-Error "Error ($($response.StatusCode)): $body"
        }
    }
    finally {
        foreach ($s in $streams) {
            $s.Dispose()
        }
    }
}
finally {
    $content.Dispose()
    $client.Dispose()
}

Write-Host "`n=== PROCESO COMPLETADO ===" -ForegroundColor Cyan
