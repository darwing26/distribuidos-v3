# Ejemplos de Peticiones HTTP para Pruebas

Este archivo contiene ejemplos de peticiones HTTP que puedes usar para probar el sistema.

## 1. Registro de Usuario

### cURL
```bash
curl -X POST http://127.0.0.1:8000/signup \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test_user",
    "email": "test@example.com",
    "password": "SecurePass123"
  }'
```

### PowerShell
```powershell
$body = @{
    username = "test_user"
    email = "test@example.com"
    password = "SecurePass123"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/signup" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"
```

### Python (requests)
```python
import requests

response = requests.post(
    "http://127.0.0.1:8000/signup",
    json={
        "username": "test_user",
        "email": "test@example.com",
        "password": "SecurePass123"
    }
)
print(response.json())
```

## 2. Login

### cURL
```bash
curl -X POST http://127.0.0.1:8000/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test_user",
    "password": "SecurePass123"
  }'
```

### PowerShell
```powershell
$loginBody = @{
    username = "test_user"
    password = "SecurePass123"
} | ConvertTo-Json

$loginResponse = Invoke-RestMethod -Uri "http://127.0.0.1:8000/login" `
    -Method POST `
    -Body $loginBody `
    -ContentType "application/json"

$usuarioId = $loginResponse.usuario_id
Write-Host "Usuario ID: $usuarioId"
```

### Python (requests)
```python
import requests

response = requests.post(
    "http://127.0.0.1:8000/login",
    json={
        "username": "test_user",
        "password": "SecurePass123"
    }
)
user_data = response.json()
usuario_id = user_data['usuario_id']
print(f"Usuario ID: {usuario_id}")
```

## 3. Procesar Imágenes - Ejemplo Simple

### cURL
```bash
curl -X POST http://127.0.0.1:8000/procesar-imagen \
  -F "usuario_id=1" \
  -F "output_format=jpg" \
  -F "files=@imagen1.jpg" \
  -F "files=@imagen2.png" \
  --output resultado.zip
```

### PowerShell
```powershell
# Forma simple con archivos
$files = @(
    Get-Item "imagen1.jpg"
    Get-Item "imagen2.png"
)

$formData = @{
    usuario_id = "1"
    output_format = "jpg"
}

# Agregar archivos manualmente
$boundary = [System.Guid]::NewGuid().ToString()
# ... (ver script completo en test_batch_processing.ps1)
```

### Python (requests)
```python
import requests

files = [
    ('files', ('imagen1.jpg', open('imagen1.jpg', 'rb'), 'image/jpeg')),
    ('files', ('imagen2.png', open('imagen2.png', 'rb'), 'image/png'))
]

data = {
    'usuario_id': 1,
    'output_format': 'jpg'
}

response = requests.post(
    'http://127.0.0.1:8000/procesar-imagen',
    data=data,
    files=files
)

# Guardar ZIP
with open('resultado.zip', 'wb') as f:
    f.write(response.content)
```

## 4. Procesar con Transformaciones por Defecto

### cURL
```bash
curl -X POST http://127.0.0.1:8000/procesar-imagen \
  -F "usuario_id=1" \
  -F "output_format=png" \
  -F 'default_transforms=[{"code":"GRAYSCALE","order":1},{"code":"RESIZE","params":{"width":800,"height":600},"order":2}]' \
  -F "files=@imagen1.jpg" \
  -F "files=@imagen2.jpg" \
  --output resultado.zip
```

### Python (requests)
```python
import requests
import json

files = [
    ('files', ('imagen1.jpg', open('imagen1.jpg', 'rb'), 'image/jpeg')),
    ('files', ('imagen2.jpg', open('imagen2.jpg', 'rb'), 'image/jpeg'))
]

default_transforms = [
    {"code": "GRAYSCALE", "order": 1},
    {"code": "RESIZE", "params": {"width": 800, "height": 600}, "order": 2}
]

data = {
    'usuario_id': 1,
    'output_format': 'png',
    'default_transforms': json.dumps(default_transforms)
}

response = requests.post(
    'http://127.0.0.1:8000/procesar-imagen',
    data=data,
    files=files
)

with open('resultado.zip', 'wb') as f:
    f.write(response.content)
```

## 5. Procesar con Instrucciones Específicas por Imagen

### Python (requests) - Ejemplo Completo
```python
import requests
import json

# Definir instrucciones específicas para cada imagen
instructions = [
    {
        "filename": "imagen1.jpg",
        "output_format": "png",
        "transforms": [
            {"code": "GRAYSCALE", "order": 1},
            {"code": "RESIZE", "params": {"width": 800, "height": 600}, "order": 2},
            {"code": "ROTATE", "params": {"degrees": 90}, "order": 3}
        ]
    },
    {
        "filename": "imagen2.jpg",
        "output_format": "jpg",
        "transforms": [
            {"code": "BLUR", "params": {"radius": 3.0}, "order": 1},
            {"code": "WATERMARK", "params": {"text": "Procesado", "x": 20, "y": 20}, "order": 2},
            {"code": "BRIGHTNESS_CONTRAST", "params": {"brightness": 1.2, "contrast": 1.1}, "order": 3}
        ]
    },
    {
        "filename": "imagen3.jpg",
        "output_format": "tif",
        "transforms": [
            {"code": "CROP", "params": {"x": 100, "y": 100, "width": 500, "height": 500}, "order": 1},
            {"code": "FLIP", "params": {"axis": "horizontal"}, "order": 2},
            {"code": "SHARPEN", "params": {"factor": 2.0}, "order": 3}
        ]
    }
]

files = [
    ('files', ('imagen1.jpg', open('imagen1.jpg', 'rb'), 'image/jpeg')),
    ('files', ('imagen2.jpg', open('imagen2.jpg', 'rb'), 'image/jpeg')),
    ('files', ('imagen3.jpg', open('imagen3.jpg', 'rb'), 'image/jpeg'))
]

data = {
    'usuario_id': 1,
    'output_format': 'jpg',  # Por defecto, si una imagen no especifica
    'instructions': json.dumps(instructions)
}

response = requests.post(
    'http://127.0.0.1:8000/procesar-imagen',
    data=data,
    files=files
)

if response.status_code == 200:
    with open('resultado.zip', 'wb') as f:
        f.write(response.content)
    print("✅ ZIP guardado: resultado.zip")
else:
    print(f"❌ Error: {response.status_code}")
    print(response.text)
```

## 6. Todas las Transformaciones - Ejemplo de Referencia

### Python - Mostrando todos los tipos de transformaciones
```python
import requests
import json

# Ejemplo con todas las 9 transformaciones disponibles
all_transforms_example = [
    {
        "filename": "demo.jpg",
        "output_format": "png",
        "transforms": [
            # 1. Escala de grises
            {"code": "GRAYSCALE", "order": 1},
            
            # 2. Redimensionar
            {"code": "RESIZE", "params": {"width": 1024, "height": 768}, "order": 2},
            
            # 3. Recortar
            {"code": "CROP", "params": {"x": 50, "y": 50, "width": 500, "height": 400}, "order": 3},
            
            # 4. Rotar
            {"code": "ROTATE", "params": {"degrees": 45}, "order": 4},
            
            # 5. Reflejar
            {"code": "FLIP", "params": {"axis": "horizontal"}, "order": 5}
        ]
    },
    {
        "filename": "demo2.jpg",
        "output_format": "jpg",
        "transforms": [
            # 6. Desenfocar
            {"code": "BLUR", "params": {"radius": 2.5}, "order": 1},
            
            # 7. Perfilar (nitidez)
            {"code": "SHARPEN", "params": {"factor": 1.8}, "order": 2},
            
            # 8. Ajustar brillo y contraste
            {"code": "BRIGHTNESS_CONTRAST", "params": {"brightness": 1.3, "contrast": 1.2}, "order": 3},
            
            # 9. Marca de agua
            {"code": "WATERMARK", "params": {"text": "© 2025 Mi Empresa", "x": 15, "y": 15}, "order": 4}
        ]
    }
]

files = [
    ('files', ('demo.jpg', open('demo.jpg', 'rb'), 'image/jpeg')),
    ('files', ('demo2.jpg', open('demo2.jpg', 'rb'), 'image/jpeg'))
]

data = {
    'usuario_id': 1,
    'instructions': json.dumps(all_transforms_example)
}

response = requests.post(
    'http://127.0.0.1:8000/procesar-imagen',
    data=data,
    files=files
)

with open('resultado_completo.zip', 'wb') as f:
    f.write(response.content)

print("✅ Todas las transformaciones aplicadas")
```

## 7. Validaciones y Manejo de Errores

### Ejemplo de error: Más de 5 transformaciones
```python
# ❌ Esto fallará porque tiene más de 5 transformaciones
invalid_transforms = {
    "filename": "imagen.jpg",
    "transforms": [
        {"code": "GRAYSCALE", "order": 1},
        {"code": "RESIZE", "params": {"width": 800, "height": 600}, "order": 2},
        {"code": "ROTATE", "params": {"degrees": 90}, "order": 3},
        {"code": "FLIP", "params": {"axis": "horizontal"}, "order": 4},
        {"code": "BLUR", "params": {"radius": 2.0}, "order": 5},
        {"code": "SHARPEN", "params": {"factor": 1.5}, "order": 6}  # ❌ Sexta transformación
    ]
}
# Error esperado: "Máximo 5 transformaciones permitidas por imagen"
```

### Ejemplo de error: Código inválido
```python
# ❌ Esto fallará porque el código no existe
invalid_code = [
    {"code": "INVALID_CODE", "order": 1}  # ❌ Código no soportado
]
# Error esperado: "Transformación no soportada: INVALID_CODE"
```

### Ejemplo de error: Parámetros faltantes
```python
# ❌ RESIZE sin dimensiones
invalid_params = [
    {"code": "RESIZE", "params": {}, "order": 1}  # ❌ Falta width y height
]
# Error esperado: "RESIZE requiere parámetros width y height válidos"
```

## 8. Formato de Respuestas

### Respuesta exitosa de Signup
```json
{
  "usuario_id": 1,
  "username": "test_user",
  "email": "test@example.com"
}
```

### Respuesta exitosa de Login
```json
{
  "usuario_id": 1,
  "username": "test_user",
  "email": "test@example.com",
  "estado": "activo"
}
```

### Respuesta exitosa de Procesamiento
- Archivo ZIP binario con todas las imágenes procesadas
- Content-Type: `application/zip`
- Content-Disposition: `attachment; filename=solicitud_123.zip`

### Respuesta de Error (400 Bad Request)
```json
{
  "detail": "Transformaciones inválidas para imagen1.jpg: RESIZE requiere parámetros width y height válidos"
}
```

### Respuesta de Error (404 Not Found)
```json
{
  "detail": "Usuario no encontrado"
}
```

## Tips para Pruebas

1. **Empezar simple**: Prueba primero sin transformaciones
2. **Una transformación a la vez**: Agrega transformaciones gradualmente
3. **Validar formatos**: Asegúrate de que los formatos de entrada sean correctos
4. **Revisar logs**: Los logs en MySQL tienen información detallada
5. **Tamaño de archivos**: Considera el tamaño de las imágenes para pruebas rápidas

## Herramientas Recomendadas

- **Postman**: Para pruebas interactivas de API
- **cURL**: Para pruebas desde línea de comandos
- **Python requests**: Para automatización
- **PowerShell**: Para scripting en Windows
