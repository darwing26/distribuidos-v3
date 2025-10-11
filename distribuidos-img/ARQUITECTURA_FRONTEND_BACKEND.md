# 🏗️ ARQUITECTURA FRONTEND-BACKEND SEPARADA

## 📊 NUEVA ARQUITECTURA

```
┌──────────────────────────────────────────────────────┐
│                     CLIENTE                          │
│  (test_frontend.py, Aplicación Web, PowerShell)     │
└──────────────────┬───────────────────────────────────┘
                   │
                   │ HTTP REST (Puerto 3000)
                   │
┌──────────────────▼───────────────────────────────────┐
│               FRONTEND API                           │
│            (frontend/app.py)                         │
│  - Gestión de sesiones                               │
│  - Validación de entrada                             │
│  - Interfaz de usuario                               │
└──────────────────┬───────────────────────────────────┘
                   │
                   │ HTTP REST (Puerto 8000)
                   │
┌──────────────────▼───────────────────────────────────┐
│               BACKEND API                            │
│            (backend/api.py)                          │
│  - Lógica de negocio                                 │
│  - Gestión de archivos                               │
│  - Comunicación con SOAP                             │
└──────────────────┬───────────────────────────────────┘
                   │
                   │ SOAP/XML (Puerto 9000)
                   │
┌──────────────────▼───────────────────────────────────┐
│            SERVICIO SOAP                             │
│         (backend/soap_service.py)                    │
│  - Registro en base de datos                         │
│  - Orquestación de trabajos                          │
└──────────────────┬───────────────────────────────────┘
                   │
                   │ gRPC (Puerto 50051+)
                   │
┌──────────────────▼───────────────────────────────────┐
│              WORKERS                                 │
│       (nodes/worker/server.py)                       │
│  - Procesamiento de imágenes                         │
│  - Aplicación de transformaciones                    │
└──────────────────────────────────────────────────────┘
```

---

## 🎯 VENTAJAS DE ESTA ARQUITECTURA

### **1. Separación de Responsabilidades**
- **Frontend:** Interfaz de usuario, validación de entrada
- **Backend:** Lógica de negocio, procesamiento de datos
- **SOAP:** Orquestación y coordinación
- **Workers:** Procesamiento intensivo

### **2. Escalabilidad**
- Cada capa puede escalar independientemente
- Frontend puede servir a múltiples clientes web/móviles
- Backend puede manejar múltiples frontends
- Workers pueden distribuirse en múltiples máquinas

### **3. Mantenibilidad**
- Cambios en la UI no afectan la lógica de negocio
- Actualizaciones del backend no requieren cambios en el frontend
- Fácil agregar nuevos endpoints

### **4. Seguridad**
- Frontend valida entrada del usuario
- Backend valida lógica de negocio
- SOAP gestiona la comunicación con workers
- Separación de credenciales por capa

---

## 🚀 CÓMO INICIAR LOS SERVICIOS

### **Opción 1: Script Automático (Recomendado)**

```powershell
cd "C:\Users\knene\OneDrive\Desktop\distribuidos v3\distribuidos-img\scripts"
.\start_frontend_backend.ps1
```

Este script abre 4 ventanas:
1. **Worker gRPC** (puerto 50051)
2. **SOAP Service** (puerto 9000)
3. **Backend API** (puerto 8000)
4. **Frontend API** (puerto 3000)

---

### **Opción 2: Manual (4 Terminales)**

#### **Terminal 1: Worker**
```powershell
cd "C:\Users\knene\OneDrive\Desktop\distribuidos v3\distribuidos-img"
.\.venv311\Scripts\Activate.ps1
python nodes/worker/server.py
```

#### **Terminal 2: SOAP**
```powershell
cd "C:\Users\knene\OneDrive\Desktop\distribuidos v3\distribuidos-img"
.\.venv311\Scripts\Activate.ps1
python -m backend.soap_service
```

#### **Terminal 3: Backend**
```powershell
cd "C:\Users\knene\OneDrive\Desktop\distribuidos v3\distribuidos-img"
.\.venv311\Scripts\Activate.ps1
uvicorn backend.api:app --host 127.0.0.1 --port 8000
```

#### **Terminal 4: Frontend**
```powershell
cd "C:\Users\knene\OneDrive\Desktop\distribuidos v3\distribuidos-img"
.\.venv311\Scripts\Activate.ps1
python frontend/app.py
```

---

## 🧪 CÓMO PROBAR LA ARQUITECTURA

### **Terminal 5: Ejecutar Prueba**
```powershell
cd "C:\Users\knene\OneDrive\Desktop\distribuidos v3\distribuidos-img"
.\.venv311\Scripts\Activate.ps1
python test_frontend.py
```

---

## 📍 FLUJO DE UNA SOLICITUD

### **Ejemplo: Procesar 3 Imágenes**

```
1. Cliente ejecuta test_frontend.py
   ↓
2. POST http://127.0.0.1:3000/signup
   Frontend valida datos → Reenvía a Backend
   ↓
3. POST http://127.0.0.1:8000/signup
   Backend crea usuario en MySQL
   ↓
4. Cliente: POST http://127.0.0.1:3000/login
   Frontend valida → Reenvía a Backend
   ↓
5. Backend verifica credenciales en MySQL
   ↓
6. Cliente: POST http://127.0.0.1:3000/procesar-imagen
   (Con 3 imágenes + transformaciones)
   ↓
7. Frontend recibe archivos → Reenvía a Backend
   ↓
8. POST http://127.0.0.1:8000/procesar-imagen
   Backend guarda archivos en data/input/
   ↓
9. Backend construye solicitud SOAP
   ↓
10. POST http://127.0.0.1:9000/ (SOAP XML)
    SOAP registra en MySQL (solicitudes, imágenes, transformaciones)
    ↓
11. SOAP llama al Orquestador
    ↓
12. Orquestador distribuye trabajos con Round-Robin
    ↓
13. gRPC a Worker (127.0.0.1:50051)
    Worker procesa cada imagen:
    - Lee de data/input/
    - Aplica transformaciones (GRAYSCALE, WATERMARK, etc.)
    - Guarda en data/output/28/
    ↓
14. Worker retorna respuesta gRPC al Orquestador
    ↓
15. Orquestador actualiza estado en MySQL
    ↓
16. SOAP marca solicitud como "completada"
    ↓
17. Backend espera que data/output/28/ tenga archivos
    ↓
18. Backend crea ZIP con todas las imágenes
    ↓
19. Backend retorna ZIP al Frontend
    ↓
20. Frontend retorna ZIP al Cliente
    ↓
21. Cliente guarda resultado_frontend_34.zip
```

---

## 🔧 ENDPOINTS DISPONIBLES

### **Frontend API (Puerto 3000)**

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Información del servicio |
| GET | `/health` | Estado del frontend y backend |
| POST | `/signup` | Registrar usuario |
| POST | `/login` | Iniciar sesión |
| POST | `/procesar-imagen` | Procesar imágenes |
| GET | `/usuarios/{id}` | Obtener info de usuario |

### **Backend API (Puerto 8000)**

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Información del servicio |
| GET | `/health` | Estado del backend |
| POST | `/signup` | Crear usuario en BD |
| POST | `/login` | Validar credenciales |
| POST | `/procesar-imagen` | Procesar imágenes vía SOAP |
| GET | `/usuarios/{id}` | Consultar usuario |

---

## 📦 ESTRUCTURA DE ARCHIVOS

```
distribuidos-img/
├── frontend/
│   └── app.py                     ← NUEVO: Frontend API
│
├── backend/
│   ├── api.py                     ← Backend API (ya existente)
│   ├── soap_service.py            ← SOAP Service
│   ├── orchestrator.py            ← Orquestador
│   ├── grpc_client.py             ← Cliente gRPC
│   ├── models.py                  ← Modelos de BD
│   └── db.py                      ← Conexión MySQL
│
├── nodes/
│   └── worker/
│       ├── server.py              ← Worker gRPC
│       └── processing.py          ← Procesamiento de imágenes
│
├── scripts/
│   ├── start_frontend_backend.ps1 ← NUEVO: Inicia 4 servicios
│   └── test_batch_processing.ps1  ← Script antiguo (usa puerto 8000)
│
├── test_frontend.py               ← NUEVO: Prueba Frontend → Backend
└── test_prueba_simple.py          ← Script antiguo (usa puerto 8000)
```

---

## 🔄 MIGRANDO CLIENTES EXISTENTES

### **Clientes que usaban Backend directo (puerto 8000)**

**ANTES:**
```python
resp = requests.post("http://127.0.0.1:8000/procesar-imagen", ...)
```

**AHORA (usando Frontend):**
```python
resp = requests.post("http://127.0.0.1:3000/procesar-imagen", ...)
```

**O mantener el uso directo del Backend:**
```python
# Todavía funciona, útil para integraciones internas
resp = requests.post("http://127.0.0.1:8000/procesar-imagen", ...)
```

---

## ⚙️ CONFIGURACIÓN

### **Cambiar Puerto del Frontend**

En `frontend/app.py`, línea final:
```python
uvicorn.run(app, host="127.0.0.1", port=3000)  # Cambiar 3000 por el puerto deseado
```

### **Cambiar URL del Backend**

En `frontend/app.py`, línea ~28:
```python
BACKEND_URL = "http://127.0.0.1:8000"  # Cambiar si backend está en otra máquina
```

---

## 🎯 CASOS DE USO

### **1. Aplicación Web**
```
Navegador → Frontend:3000 → Backend:8000 → SOAP → Workers
```

### **2. Aplicación Móvil**
```
App Móvil → Frontend:3000 → Backend:8000 → SOAP → Workers
```

### **3. Integración Interna (sin Frontend)**
```
Sistema Interno → Backend:8000 → SOAP → Workers
```

### **4. Microservicios (múltiples frontends)**
```
Web Frontend:3000 ─┐
                   ├→ Backend:8000 → SOAP → Workers
Mobile Frontend:3001 ┘
```

---

## ✅ VERIFICACIÓN

Después de iniciar todos los servicios, verifica:

```powershell
# Verificar puertos
netstat -ano | findstr "LISTENING" | findstr ":3000\|:8000\|:9000\|:50051"
```

Deberías ver:
```
TCP    127.0.0.1:3000         LISTENING       # Frontend
TCP    127.0.0.1:8000         LISTENING       # Backend
TCP    0.0.0.0:9000           LISTENING       # SOAP
TCP    0.0.0.0:50051          LISTENING       # Worker
```

---

## 🐛 SOLUCIÓN DE PROBLEMAS

### **Frontend no puede conectar con Backend**

**Error:** `Backend no disponible: Connection refused`

**Solución:**
1. Verifica que Backend esté corriendo: `netstat -ano | findstr :8000`
2. Revisa la URL en `frontend/app.py`: `BACKEND_URL = "http://127.0.0.1:8000"`

### **Backend no puede conectar con SOAP**

**Error:** `SOAP error: Connection refused`

**Solución:**
1. Verifica que SOAP esté corriendo: `netstat -ano | findstr :9000`
2. Revisa la URL en `backend/api.py`: `SOAP_URL = "http://127.0.0.1:9000/"`

---

## 📚 DOCUMENTACIÓN ADICIONAL

- `RASTREO_FLUJO_COMPLETO.md` - Flujo detallado completo
- `GUIA_RAPIDA_PRUEBA.md` - Comandos rápidos
- `GUIA_WATERMARK.md` - Uso de transformaciones

---

¡Arquitectura Frontend-Backend lista! 🚀
