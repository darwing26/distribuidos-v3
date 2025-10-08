# Sistema Distribuido de Procesamiento de Imágenes

Sistema de procesamiento distribuido que permite aplicar múltiples transformaciones a lotes de imágenes, con soporte para hasta 5 transformaciones por imagen y exportación en archivo ZIP.

## Características Principales

### Transformaciones Soportadas (hasta 5 por imagen)

1. **GRAYSCALE** - Conversión a escala de grises
2. **RESIZE** - Redimensionar con ancho y alto específicos
3. **CROP** - Recortar región específica
4. **ROTATE** - Rotar en grados
5. **FLIP** - Reflejar horizontal o verticalmente
6. **BLUR** - Aplicar desenfoque gaussiano
7. **SHARPEN** - Aumentar nitidez
8. **BRIGHTNESS_CONTRAST** - Ajustar brillo y contraste
9. **WATERMARK** - Insertar texto o marca de agua

### Formatos de Salida

- **JPG** - JPEG comprimido
- **PNG** - PNG con transparencia
- **TIF** - TIFF sin pérdida

## Instalación

### 1. Crear entorno virtual e instalar dependencias

**Windows (PowerShell)**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Linux/macOS**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Generar stubs gRPC

```bash
python -m grpc_tools.protoc -I backend/grpc_proto --python_out=backend/grpc_proto --grpc_python_out=backend/grpc_proto backend/grpc_proto/image_worker.proto
python -m grpc_tools.protoc -I nodes/grpc_proto --python_out=nodes/grpc_proto --grpc_python_out=nodes/grpc_proto nodes/grpc_proto/image_worker.proto
```

### 3. Configurar base de datos MySQL

Ejecutar el script SQL `schema.sql` para crear las tablas necesarias.

## Ejecución

### Levantar los servicios (en terminales separadas)

1. **Nodo Worker gRPC**
```bash
python nodes/worker/server.py
```

2. **Servidor SOAP**
```bash
python backend/soap_service.py
```

3. **API Cliente FastAPI**
```bash
uvicorn backend.api:app --reload
```

## Uso de la API

### 1. Registro de Usuario

**POST** `/signup`

```json
{
  "username": "usuario_demo",
  "email": "demo@example.com",
  "password": "password123"
}
```

**Respuesta:**
```json
{
  "usuario_id": 1,
  "username": "usuario_demo",
  "email": "demo@example.com"
}
```

### 2. Login

**POST** `/login`

```json
{
  "username": "usuario_demo",
  "password": "password123"
}
```

**Respuesta:**
```json
{
  "usuario_id": 1,
  "username": "usuario_demo",
  "email": "demo@example.com",
  "estado": "activo"
}
```

### 3. Procesar Lote de Imágenes

**POST** `/procesar-imagen` (multipart/form-data)

**Parámetros:**

- `usuario_id` (int, requerido) - ID del usuario autenticado
- `output_format` (string, opcional) - Formato de salida por defecto: `jpg`, `png` o `tif`
- `default_transforms` (JSON string, opcional) - Transformaciones aplicadas a todas las imágenes que no tengan instrucciones específicas
- `instructions` (JSON string, opcional) - Instrucciones específicas por imagen
- `files` (archivos, requerido) - Una o más imágenes a procesar

**Respuesta:** Archivo ZIP con todas las imágenes procesadas

## Ejemplos de Uso

### Ejemplo 1: Transformaciones por Defecto

Aplicar las mismas transformaciones a todas las imágenes:

```json
{
  "default_transforms": [
    { "code": "GRAYSCALE", "order": 1 },
    { "code": "RESIZE", "params": { "width": 800, "height": 600 }, "order": 2 }
  ]
}
```

### Ejemplo 2: Instrucciones Específicas por Imagen

Diferentes transformaciones para cada imagen:

```json
{
  "instructions": [
    {
      "filename": "imagen1.jpg",
      "output_format": "png",
      "transforms": [
        { "code": "GRAYSCALE", "order": 1 },
        { "code": "ROTATE", "params": { "degrees": 90 }, "order": 2 },
        { "code": "WATERMARK", "params": { "text": "Procesado", "x": 10, "y": 10 }, "order": 3 }
      ]
    },
    {
      "filename": "imagen2.jpg",
      "output_format": "jpg",
      "transforms": [
        { "code": "RESIZE", "params": { "width": 1024, "height": 768 }, "order": 1 },
        { "code": "SHARPEN", "params": { "factor": 2.0 }, "order": 2 },
        { "code": "BRIGHTNESS_CONTRAST", "params": { "brightness": 1.2, "contrast": 1.1 }, "order": 3 }
      ]
    }
  ]
}
```

## Referencia de Transformaciones

### GRAYSCALE
Convierte la imagen a escala de grises.

```json
{ "code": "GRAYSCALE" }
```

### RESIZE
Redimensiona la imagen al tamaño especificado.

```json
{
  "code": "RESIZE",
  "params": {
    "width": 800,
    "height": 600
  }
}
```

### CROP
Recorta una región específica de la imagen.

```json
{
  "code": "CROP",
  "params": {
    "x": 100,
    "y": 100,
    "width": 500,
    "height": 500
  }
}
```

### ROTATE
Rota la imagen en grados (sentido antihorario).

```json
{
  "code": "ROTATE",
  "params": {
    "degrees": 90
  }
}
```

### FLIP
Refleja la imagen horizontal o verticalmente.

```json
{
  "code": "FLIP",
  "params": {
    "axis": "horizontal"  // o "vertical"
  }
}
```

### BLUR
Aplica desenfoque gaussiano.

```json
{
  "code": "BLUR",
  "params": {
    "radius": 2.0
  }
}
```

### SHARPEN
Aumenta la nitidez de la imagen.

```json
{
  "code": "SHARPEN",
  "params": {
    "factor": 1.5
  }
}
```

### BRIGHTNESS_CONTRAST
Ajusta brillo y contraste (1.0 = sin cambio).

```json
{
  "code": "BRIGHTNESS_CONTRAST",
  "params": {
    "brightness": 1.2,
    "contrast": 1.1
  }
}
```

### WATERMARK
Inserta texto como marca de agua.

```json
{
  "code": "WATERMARK",
  "params": {
    "text": "Copyright 2025",
    "x": 10,
    "y": 10
  }
}
```

## Script de Prueba

El script PowerShell `test_batch_processing.ps1` proporciona un ejemplo completo:

```powershell
.\scripts\test_batch_processing.ps1 -ImagePaths @("imagen1.jpg","imagen2.png","imagen3.jpg")
```

Este script:
1. Registra un usuario nuevo
2. Inicia sesión
3. Envía múltiples imágenes con transformaciones específicas
4. Descarga el archivo ZIP con las imágenes procesadas

## Arquitectura

```
Cliente (FastAPI)
    ↓ HTTP
Orquestador (SOAP)
    ↓ gRPC
Worker (Pillow)
    ↓
Base de Datos (MySQL)
```

### Componentes

- **backend/api.py**: API REST que recibe requests HTTP
- **backend/soap_service.py**: Servicio SOAP que coordina el procesamiento
- **nodes/worker/server.py**: Worker gRPC que procesa las imágenes
- **nodes/worker/processing.py**: Lógica de transformaciones con Pillow

## Limitaciones

- Máximo **5 transformaciones por imagen**
- Formatos soportados: JPG, PNG, TIF
- Las transformaciones se aplican en el orden especificado por el campo `order`
- El archivo ZIP se genera después de procesar todas las imágenes

## Logging

Todas las operaciones se registran en la tabla `logs` de MySQL con:
- Timestamp
- Componente (api, soap, worker)
- Nivel (info, error)
- Mensaje
- ID de solicitud (opcional)
- ID de imagen (opcional)

## Desarrollo

Para contribuir al proyecto:

1. Fork del repositorio
2. Crear rama de feature
3. Implementar cambios con tests
4. Enviar pull request

## Licencia

MIT License
