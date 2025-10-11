"""
Frontend API - Cliente que consume el Backend
==============================================
Este es el servidor frontend que se comunica con el backend vía REST API.
Los usuarios/aplicaciones interactúan con este frontend.

Puertos:
- Frontend: 3000
- Backend: 8000
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List
import httpx
import json
import bcrypt
from backend.models import (
    crear_usuario,
    obtener_usuario_por_username,
    obtener_usuario_por_email,
    obtener_usuario_por_id
)

app = FastAPI(title="Frontend Cliente API", version="1.0.0")

# Configurar CORS para permitir peticiones desde navegadores
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especifica los orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# URL del backend (el servidor que se comunica con SOAP)
BACKEND_URL = "http://127.0.0.1:8000"

# =============================================================================
# MODELOS DE DATOS
# =============================================================================

class SignupRequest(BaseModel):
    """Modelo para registro de usuario"""
    username: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    """Modelo para inicio de sesión"""
    username: str
    password: str

# =============================================================================
# ENDPOINT: Health Check
# =============================================================================

@app.get("/")
async def root():
    """
    Endpoint raíz - Información del servicio
    """
    return {
        "service": "Frontend API",
        "version": "1.0.0",
        "status": "running",
        "backend": BACKEND_URL
    }

@app.get("/health")
async def health_check():
    """
    Verificar estado del frontend y backend
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            backend_resp = await client.get(f"{BACKEND_URL}/health")
            backend_status = "ok" if backend_resp.status_code == 200 else "error"
    except:
        backend_status = "unreachable"
    
    return {
        "frontend": "ok",
        "backend": backend_status,
        "backend_url": BACKEND_URL
    }

# =============================================================================
# ENDPOINT: Registro de Usuario
# =============================================================================

@app.post("/signup")
async def signup(request: SignupRequest):
    """
    Registrar un nuevo usuario
    
    Crea un nuevo usuario directamente en la base de datos del frontend.
    """
    # Validar si el username ya existe
    if obtener_usuario_por_username(request.username):
        raise HTTPException(status_code=400, detail="El username ya existe")
    
    # Validar si el email ya existe
    if obtener_usuario_por_email(request.email):
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    # Hash de la contraseña
    pass_hash = bcrypt.hashpw(request.password.encode(), bcrypt.gensalt()).decode()
    
    # Crear usuario
    try:
        usuario_id = crear_usuario(request.username, request.email, pass_hash)
        return {
            "message": "Usuario creado exitosamente",
            "usuario_id": usuario_id,
            "username": request.username
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear usuario: {str(e)}")

# =============================================================================
# ENDPOINT: Inicio de Sesión
# =============================================================================

@app.post("/login")
async def login(request: LoginRequest):
    """
    Iniciar sesión
    
    Valida las credenciales del usuario directamente en la base de datos.
    """
    # Buscar usuario
    usuario = obtener_usuario_por_username(request.username)
    
    if not usuario:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    
    # Verificar contraseña
    if not bcrypt.checkpw(request.password.encode(), usuario["pass_hash"].encode()):
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")
    
    # Verificar estado del usuario
    if usuario.get("estado") != "activo":
        raise HTTPException(status_code=403, detail="Usuario inactivo")
    
    return {
        "message": "Login exitoso",
        "usuario_id": usuario["id"],
        "username": usuario["username"],
        "email": usuario["email"]
    }

# =============================================================================
# ENDPOINT: Procesamiento de Imágenes
# =============================================================================

@app.post("/procesar-imagen")
async def procesar_imagen(
    usuario_id: int = Form(...),
    output_format: str = Form("jpg"),
    instructions: str | None = Form(None),
    files: List[UploadFile] = File(...)
):
    """
    Procesar un lote de imágenes con transformaciones
    
    Args:
        usuario_id: ID del usuario autenticado
        output_format: Formato de salida por defecto (jpg, png, tif)
        instructions: JSON con instrucciones específicas por imagen
        files: Lista de archivos de imagen a procesar
    
    Returns:
        ZIP con todas las imágenes procesadas
    
    Flujo:
        Frontend → Backend → SOAP → Orquestador → Workers
    """
    try:
        # Preparar los datos para el backend
        async with httpx.AsyncClient(timeout=180.0) as client:
            # Crear el form data para el backend
            files_data = []
            for upload_file in files:
                # Leer el contenido del archivo
                content = await upload_file.read()
                files_data.append(
                    ("files", (upload_file.filename, content, upload_file.content_type))
                )
                # Resetear el puntero para permitir releer si es necesario
                await upload_file.seek(0)
            
            # Preparar los datos del formulario
            form_data = {
                "usuario_id": str(usuario_id),
                "output_format": output_format,
            }
            
            if instructions:
                form_data["instructions"] = instructions
            
            # Enviar al backend
            resp = await client.post(
                f"{BACKEND_URL}/procesar-imagen",
                data=form_data,
                files=files_data
            )
            
            if resp.status_code == 200:
                # Retornar el ZIP tal como lo recibió del backend
                return Response(
                    content=resp.content,
                    media_type="application/zip",
                    headers={
                        "Content-Disposition": resp.headers.get(
                            "Content-Disposition",
                            "attachment; filename=imagenes_procesadas.zip"
                        )
                    }
                )
            else:
                # Intentar parsear el error del backend
                try:
                    error_detail = resp.json().get("detail", "Error en el backend")
                except:
                    error_detail = resp.text
                
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=error_detail
                )
    
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Timeout: El procesamiento tardó demasiado"
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Backend no disponible: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error inesperado: {str(e)}"
        )

# =============================================================================
# ENDPOINT: Obtener información del usuario
# =============================================================================

@app.get("/usuarios/{usuario_id}")
async def obtener_usuario(usuario_id: int):
    """
    Obtener información de un usuario
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{BACKEND_URL}/usuarios/{usuario_id}")
            
            if resp.status_code == 200:
                return resp.json()
            else:
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=resp.json().get("detail", "Usuario no encontrado")
                )
    
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Backend no disponible: {str(e)}"
        )

# =============================================================================
# INICIALIZACIÓN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*70)
    print("🌐 FRONTEND API - Servidor Cliente")
    print("="*70)
    print(f"📍 Frontend escuchando en: http://127.0.0.1:3000")
    print(f"🔗 Backend conectado a: {BACKEND_URL}")
    print("="*70 + "\n")
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=3000,
        log_level="info"
    )
