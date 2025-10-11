# 📦 CAMBIO A BASE64 - ENVÍO DE IMÁGENES

## ✅ CAMBIOS REALIZADOS

### **ANTES (Con archivos en disco):**

```
Cliente → Backend:
  - Envía archivos multipart/form-data
  - Backend guarda archivos en data/input/
  - Backend envía rutas de archivo al SOAP
  
Backend → SOAP:
  - Payload: { "input_path": "/ruta/archivo.jpg" }
  - SOAP lee archivos desde disco
  - SOAP registra en BD y orquesta
```

### **AHORA (Con base64):**

```
Cliente → Backend:
  - Envía archivos multipart/form-data
  - Backend lee archivos en memoria
  - Backend convierte a base64
  
Backend → SOAP:
  - Payload: { "image_data": "iVBORw0KGgo..." }
  - SOAP decodifica base64
  - SOAP guarda en data/input/
  - SOAP registra en BD y orquesta
```

---

## 📝 CÓDIGO MODIFICADO

### **1. Backend API (`backend/api.py`)**

**Import agregado:**
```python
import base64
```

**Lógica modificada en `/procesar-imagen`:**

**ANTES:**
```python
# Guardaba archivos en disco primero
filename = f"{uuid.uuid4()}_{safe_name}"
input_path = os.path.join("data", "input", filename)
with open(input_path, "wb") as f:
    shutil.copyfileobj(upload.file, f)

payload = {
    "original_name": upload.filename,
    "input_path": input_path,  # ← Enviaba ruta
    "input_format": "jpg",
    "output_format": "jpg",
    "transforms": [...]
}
```

**AHORA:**
```python
# Lee la imagen y la convierte a base64
image_bytes = await upload.read()
image_base64 = base64.b64encode(image_bytes).decode('utf-8')
imagen_id = str(uuid.uuid4())

payload = {
    "imagen_id": imagen_id,           # ← ID único
    "original_name": upload.filename,
    "image_data": image_base64,       # ← Datos base64
    "input_format": "jpg",
    "output_format": "jpg",
    "transforms": [...]
}
```

---

### **2. Servicio SOAP (`backend/soap_service.py`)**

**Import agregado:**
```python
import base64
```

**Lógica modificada en `crearSolicitud`:**

**ANTES:**
```python
payload = _parse_imagen_payload(raw)
input_path = payload.get("input_path")  # ← Recibía ruta

nombre = payload.get("original_name") or os.path.basename(input_path)
# Asumía que el archivo ya existía en disco
```

**AHORA:**
```python
payload = _parse_imagen_payload(raw)

# Obtiene datos base64
imagen_id_uuid = payload.get("imagen_id")
image_base64 = payload.get("image_data")

# Decodifica base64
image_bytes = base64.b64decode(image_base64)

# Crea directorio
os.makedirs("data/input", exist_ok=True)

# Guarda archivo en disco
filename = f"{imagen_id_uuid}_{safe_name}"
input_path = os.path.join("data", "input", filename)
with open(input_path, "wb") as f:
    f.write(image_bytes)

log(f"Imagen guardada en {input_path}")
```

---

## 🔄 FLUJO ACTUALIZADO

```
1. Cliente → Backend:3000/procesar-imagen
   FormData: files=[imagen1.jpg, imagen2.png]

2. Backend (api.py):
   ┌─────────────────────────────────────┐
   │ for upload in files:                │
   │   image_bytes = await upload.read() │
   │   base64_str = base64encode(bytes)  │
   │   payload = {                       │
   │     "imagen_id": uuid(),            │
   │     "image_data": base64_str,       │
   │     ...                             │
   │   }                                 │
   └─────────────────────────────────────┘
   
3. Backend → SOAP:9000/crearSolicitud
   XML SOAP con payloads JSON que contienen base64

4. SOAP (soap_service.py):
   ┌──────────────────────────────────────┐
   │ for payload in imagenes:            │
   │   image_base64 = payload["image_data"] │
   │   image_bytes = base64decode(base64) │
   │   save to data/input/{uuid}_name.jpg │
   │   registrar_imagen(solicitud_id, ...)│
   └──────────────────────────────────────┘

5. SOAP → Orchestrator → Workers
   Procesa imágenes desde data/input/

6. Workers → data/output/{solicitud_id}/
   Guarda imágenes procesadas

7. Backend → Cliente
   Retorna ZIP con imágenes procesadas
```

---

## ✅ VENTAJAS DEL CAMBIO

| Aspecto | Antes | Ahora |
|---------|-------|-------|
| **Almacenamiento temporal** | Backend guardaba en disco | Backend solo en memoria |
| **Transferencia** | Rutas de archivo | Datos directos (base64) |
| **Portabilidad** | Dependía de sistema de archivos compartido | Funciona en cualquier entorno |
| **Escalabilidad** | Backend y SOAP deben compartir disco | Backend y SOAP pueden estar en máquinas diferentes |
| **Limpieza** | Archivos temporales en Backend | Solo en SOAP (después de procesar) |

---

## 🧪 PRUEBA

```powershell
# 1. Iniciar servicios
cd scripts
.\start_frontend_backend.ps1

# 2. Ejecutar test
cd ..
python test_frontend.py
```

**Resultado esperado:**
```
✅ Imágenes enviadas al backend
✅ Backend convierte a base64
✅ SOAP recibe base64 y decodifica
✅ SOAP guarda en data/input/
✅ Procesamiento continúa normalmente
✅ ZIP creado exitosamente
```

---

## 📋 PAYLOAD EJEMPLO

**Backend → SOAP (JSON dentro del XML):**
```json
{
  "imagen_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "original_name": "foto.jpg",
  "image_data": "/9j/4AAQSkZJRgABAQEAYABgAAD...",
  "input_format": "jpg",
  "output_format": "png",
  "transforms": [
    {
      "code": "GRAYSCALE",
      "params": {},
      "order": 1
    },
    {
      "code": "WATERMARK",
      "params": {
        "text": "PROCESADO",
        "position": "center"
      },
      "order": 2
    }
  ]
}
```

---

## 🎯 ARCHIVOS MODIFICADOS

- ✅ `backend/api.py` - Convierte imágenes a base64 antes de enviar
- ✅ `backend/soap_service.py` - Decodifica base64 y guarda en disco

**No requiere cambios:**
- ✅ `backend/orchestrator.py` - Sigue funcionando igual
- ✅ `nodes/worker/server.py` - Sigue funcionando igual
- ✅ `frontend/app.py` - Sigue funcionando igual

---

## 🚀 SIGUIENTE PASO

El sistema ahora **NO** crea archivos XML adicionales. Las imágenes viajan como **base64 dentro del JSON** que va en el payload SOAP.

¡Todo funciona de manera más limpia y portable! 🎉
