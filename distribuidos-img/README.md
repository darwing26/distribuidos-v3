# Sistema Distribuido de Procesamiento de Imágenes

## 🎯 Características Principales

- **Procesamiento en Lote**: Procesa múltiples imágenes simultáneamente
- **Hasta 5 Transformaciones por Imagen**: Combina hasta 5 operaciones diferentes
- **Instrucciones Personalizadas**: Define transformaciones específicas para cada imagen
- **Exportación ZIP**: Recibe todas las imágenes procesadas en un solo archivo
- **9 Tipos de Transformaciones**: Escala de grises, redimensionar, recortar, rotar, reflejar, desenfocar, perfilar, ajustar brillo/contraste, marcas de agua
- **3 Formatos de Salida**: JPG, PNG, TIF

## 📦 Instalación Rápida

### 1. Instalar Dependencias

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

> **Nota:** Si PowerShell bloquea scripts, ejecuta: `Set-ExecutionPolicy -Scope Process Bypass`

### 2. Generar Stubs gRPC

```bash
python -m grpc_tools.protoc -I backend/grpc_proto --python_out=backend/grpc_proto --grpc_python_out=backend/grpc_proto backend/grpc_proto/image_worker.proto
python -m grpc_tools.protoc -I nodes/grpc_proto --python_out=nodes/grpc_proto --grpc_python_out=nodes/grpc_proto nodes/grpc_proto/image_worker.proto
```

### 3. Configurar Base de Datos

Ejecuta el script SQL `backend/schema.sql` en tu servidor MySQL para crear las tablas necesarias.

### 4. Levantar los Servicios

Abre **3 terminales diferentes** y ejecuta:

**Terminal 1 - Worker gRPC**
```bash
python nodes/worker/server.py
```

**Terminal 2 - Servidor SOAP**
```bash
python backend/soap_service.py
```

**Terminal 3 - API FastAPI**
```bash
uvicorn backend.api:app --reload
```

La API estará disponible en: `http://127.0.0.1:8000`  
WSDL SOAP en: `http://127.0.0.1:9000/?wsdl`

## 🚀 Inicio Rápido

### Prueba con el Script Automatizado

```powershell
cd scripts
.\test_batch_processing.ps1 -ImagePaths @("..\img\imagen1.png","..\img\imagen2.png")
```

Este script:
1. ✅ Registra un usuario automáticamente
2. ✅ Inicia sesión
3. ✅ Envía las imágenes con transformaciones
4. ✅ Descarga el archivo ZIP con los resultados

### Ejemplo con Python

```bash
cd examples
python batch_processing_example.py
```

## 📖 API Reference

### Endpoints

#### POST `/signup` - Registro de Usuario

```json
{
  "username": "usuario_demo",
  "email": "demo@example.com",
  "password": "secreto123"
}
```

**Respuesta:** `{ "usuario_id": 1, "username": "usuario_demo", ... }`

#### POST `/login` - Iniciar Sesión

```json
{
  "username": "usuario_demo",
  "password": "secreto123"
}
```

**Respuesta:** `{ "usuario_id": 1, "username": "usuario_demo", "estado": "activo" }`

#### POST `/procesar-imagen` - Procesar Lote de Imágenes

Envía un formulario `multipart/form-data` con:

**Parámetros:**
- `usuario_id` (int, requerido) - ID del usuario
- `output_format` (string) - Formato por defecto: `jpg`, `png` o `tif`
- `default_transforms` (JSON) - Transformaciones aplicadas a todas las imágenes
- `instructions` (JSON) - Instrucciones específicas por imagen
- `files` (archivos) - Una o más imágenes

**Respuesta:** Archivo ZIP con todas las imágenes procesadas

## 🎨 Transformaciones Disponibles

Puedes aplicar hasta **5 transformaciones por imagen**:

| Código | Descripción | Parámetros |
|--------|-------------|------------|
| `GRAYSCALE` | Escala de grises | Ninguno |
| `RESIZE` | Redimensionar | `width`, `height` |
| `CROP` | Recortar región | `x`, `y`, `width`, `height` |
| `ROTATE` | Rotar imagen | `degrees` |
| `FLIP` | Reflejar | `axis` (horizontal/vertical) |
| `BLUR` | Desenfocar | `radius` |
| `SHARPEN` | Aumentar nitidez | `factor` |
| `BRIGHTNESS_CONTRAST` | Ajustar brillo/contraste | `brightness`, `contrast` |
| `WATERMARK` | Marca de agua | `text`, `x`, `y` |

## 💡 Ejemplos de Uso

### Ejemplo 1: Transformaciones Simples

```json
{
  "default_transforms": [
    { "code": "GRAYSCALE", "order": 1 },
    { "code": "RESIZE", "params": { "width": 800, "height": 600 }, "order": 2 }
  ]
}
```

### Ejemplo 2: Instrucciones por Imagen

```json
{
  "instructions": [
    {
      "filename": "foto1.jpg",
      "output_format": "png",
      "transforms": [
        { "code": "ROTATE", "params": { "degrees": 90 }, "order": 1 },
        { "code": "WATERMARK", "params": { "text": "© 2025", "x": 10, "y": 10 }, "order": 2 },
        { "code": "SHARPEN", "params": { "factor": 2.0 }, "order": 3 }
      ]
    },
    {
      "filename": "foto2.jpg",
      "output_format": "jpg",
      "transforms": [
        { "code": "CROP", "params": { "x": 100, "y": 100, "width": 500, "height": 500 }, "order": 1 },
        { "code": "BLUR", "params": { "radius": 3.0 }, "order": 2 }
      ]
    }
  ]
}
```

## 📂 Estructura del Proyecto

```
distribuidos-img/
├── backend/
│   ├── api.py              # API REST FastAPI
│   ├── soap_service.py     # Servicio SOAP
│   ├── grpc_client.py      # Cliente gRPC
│   ├── models.py           # Acceso a datos
│   └── schema.sql          # Esquema de BD
├── nodes/
│   └── worker/
│       ├── server.py       # Worker gRPC
│       └── processing.py   # Lógica de transformaciones
├── scripts/
│   └── test_batch_processing.ps1  # Script de prueba
├── examples/
│   └── batch_processing_example.py  # Ejemplo Python
└── DOCUMENTATION.md        # Documentación completa
```

## 🔄 Arquitectura

```
Cliente → FastAPI → SOAP → gRPC Worker → Pillow
                      ↓
                   MySQL DB
```

1. Cliente envía imágenes vía HTTP
2. FastAPI valida y prepara payload SOAP
3. Servicio SOAP coordina con base de datos
4. Worker gRPC procesa imágenes con Pillow
5. Respuesta con archivo ZIP

## 📝 Documentación Completa

Ver [DOCUMENTATION.md](DOCUMENTATION.md) para:
- Referencia completa de transformaciones
- Ejemplos avanzados
- Guía de desarrollo
- Troubleshooting
