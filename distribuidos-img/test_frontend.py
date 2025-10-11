"""
🧪 Script de Prueba - Frontend API
===================================
Este script prueba la comunicación:
Cliente → Frontend (puerto 3000) → Backend (puerto 8000) → SOAP → Workers
"""

import requests
import json
import os

FRONTEND_URL = "http://127.0.0.1:3000"  # ← Ahora usamos el FRONTEND

print("\n" + "="*70)
print("🧪 PRUEBA DE ARQUITECTURA FRONTEND → BACKEND")
print("="*70 + "\n")

# =============================================================================
# PASO 1: Verificar que ambos servicios estén activos
# =============================================================================
print("[1/6] 🔍 Verificando servicios...")

try:
    resp = requests.get(f"{FRONTEND_URL}/health", timeout=5)
    health = resp.json()
    
    print(f"      ✅ Frontend: {health['frontend']}")
    print(f"      ✅ Backend: {health['backend']}")
    
    if health['backend'] != 'ok':
        print("\n      ⚠️  El backend no está disponible")
        print("      Asegúrate de que esté corriendo en puerto 8000")
        exit(1)
        
except Exception as e:
    print(f"      ❌ Error: {e}")
    print("\n      Asegúrate de iniciar:")
    print("      1. Backend en puerto 8000")
    print("      2. Frontend en puerto 3000")
    exit(1)

# =============================================================================
# PASO 2: Registro de Usuario
# =============================================================================
print("\n[2/6] 📝 Registrando usuario...")

signup_data = {
    "username": "frontend_test_user",
    "email": "frontend@example.com",
    "password": "Frontend123"
}

try:
    resp = requests.post(f"{FRONTEND_URL}/signup", json=signup_data, timeout=10)
    if resp.status_code == 200:
        usuario_id = resp.json()["usuario_id"]
        print(f"      ✅ Usuario registrado: ID={usuario_id}")
    else:
        print(f"      ℹ️  Usuario ya existe")
        usuario_id = None
except Exception as e:
    print(f"      ⚠️  Error: {e}")
    usuario_id = None

# =============================================================================
# PASO 3: Inicio de Sesión
# =============================================================================
print("\n[3/6] 🔐 Iniciando sesión...")

login_data = {
    "username": "frontend_test_user",
    "password": "Frontend123"
}

try:
    resp = requests.post(f"{FRONTEND_URL}/login", json=login_data, timeout=10)
    if resp.status_code == 200:
        usuario_id = resp.json()["usuario_id"]
        print(f"      ✅ Sesión iniciada: ID={usuario_id}")
        print(f"      👤 Usuario: {resp.json()['username']}")
    else:
        print(f"      ❌ Error de login: {resp.text}")
        exit(1)
except Exception as e:
    print(f"      ❌ Error: {e}")
    exit(1)

# =============================================================================
# PASO 4: Buscar Imágenes
# =============================================================================
print("\n[4/6] 🖼️  Buscando imágenes...")

# Buscar imágenes en data/input
image_dir = "data/input"
if not os.path.exists(image_dir):
    print(f"      ❌ No se encontró la carpeta '{image_dir}'")
    print("      💡 Asegúrate de tener imágenes en data/input/")
    exit(1)

image_files = []
for filename in os.listdir(image_dir):
    if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
        image_files.append(filename)
        if len(image_files) >= 3:
            break

if not image_files:
    print(f"      ❌ No se encontraron imágenes en '{image_dir}'")
    print("      💡 Copia algunas imágenes a data/input/ para probar")
    exit(1)

print(f"      ✅ Encontradas {len(image_files)} imagen(es):")
for img in image_files:
    print(f"         • {img}")

# =============================================================================
# PASO 5: Preparar Transformaciones
# =============================================================================
print("\n[5/6] 🎨 Preparando transformaciones...")

instructions = []

# Imagen 1: Escala de grises + Marca de agua FRONTEND
if len(image_files) > 0:
    instructions.append({
        "filename": image_files[0],
        "output_format": "jpg",
        "transforms": [
            {"code": "GRAYSCALE", "order": 1},
            {"code": "WATERMARK", "params": {
                "text": "VIA FRONTEND",
                "x": 50,
                "y": 50,
                "font_size": 70,
                "color": "orange",
                "opacity": 220
            }, "order": 2}
        ]
    })
    print(f"      • {image_files[0]}: GRAYSCALE + WATERMARK (naranja)")

# Imagen 2: Rotar + Marca de agua
if len(image_files) > 1:
    instructions.append({
        "filename": image_files[1],
        "output_format": "jpg",
        "transforms": [
            {"code": "ROTATE", "params": {"degrees": 45}, "order": 1},
            {"code": "WATERMARK", "params": {
                "text": "ARQUITECTURA",
                "x": 100,
                "y": 100,
                "font_size": 55,
                "color": "cyan",
                "opacity": 200
            }, "order": 2}
        ]
    })
    print(f"      • {image_files[1]}: ROTATE + WATERMARK (cian)")

# Imagen 3: Blur + Marca de agua
if len(image_files) > 2:
    instructions.append({
        "filename": image_files[2],
        "output_format": "png",
        "transforms": [
            {"code": "BLUR", "params": {"radius": 2.0}, "order": 1},
            {"code": "WATERMARK", "params": {
                "text": "3 CAPAS",
                "x": 150,
                "y": 150,
                "font_size": 45,
                "color": "magenta",
                "opacity": 180
            }, "order": 2}
        ]
    })
    print(f"      • {image_files[2]}: BLUR + WATERMARK (magenta)")

# =============================================================================
# PASO 6: Enviar Solicitud al FRONTEND
# =============================================================================
print("\n[6/6] 🚀 Enviando solicitud al FRONTEND...")
print("      📍 Ruta: Frontend → Backend → SOAP → Workers")
print("      (Esto puede tardar unos segundos...)\n")

# Preparar archivos
files = []
for filename in image_files:
    filepath = os.path.join(image_dir, filename)
    files.append(("files", (filename, open(filepath, "rb"), "image/jpeg")))

# Preparar datos
data = {
    "usuario_id": usuario_id,
    "output_format": "jpg",
    "instructions": json.dumps(instructions)
}

try:
    resp = requests.post(
        f"{FRONTEND_URL}/procesar-imagen",  # ← FRONTEND, no BACKEND
        data=data,
        files=files,
        timeout=180
    )
    
    if resp.status_code == 200:
        # Guardar ZIP
        output_filename = f"resultado_frontend_{usuario_id}.zip"
        with open(output_filename, "wb") as f:
            f.write(resp.content)
        
        print("="*70)
        print("✅ ¡ÉXITO! Arquitectura Frontend → Backend funcionando")
        print("="*70)
        print(f"\n📦 Archivo ZIP creado: {output_filename}")
        print(f"📊 Tamaño: {len(resp.content):,} bytes ({len(resp.content)/1024:.2f} KB)")
        print(f"\n🔄 Flujo completado:")
        print(f"   Cliente → Frontend:3000 → Backend:8000 → SOAP:9000 → Worker:50051")
        print(f"\n💡 Descomprime el ZIP para ver las imágenes procesadas")
        print("="*70 + "\n")
    else:
        print("="*70)
        print("❌ ERROR EN EL PROCESAMIENTO")
        print("="*70)
        print(f"Código: {resp.status_code}")
        print(f"Mensaje: {resp.text}")
        print("="*70 + "\n")
        
except requests.exceptions.Timeout:
    print("❌ Timeout: El procesamiento tardó demasiado")
except Exception as e:
    print(f"❌ Error inesperado: {e}")
