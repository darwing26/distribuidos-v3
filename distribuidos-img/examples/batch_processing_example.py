"""
Ejemplo de uso del API de procesamiento de imágenes en lote.

Este script demuestra cómo:
1. Registrar un usuario
2. Iniciar sesión
3. Enviar múltiples imágenes con transformaciones específicas
4. Recibir y guardar el archivo ZIP con las imágenes procesadas
"""

import requests
import json
from pathlib import Path

# Configuración
API_BASE = "http://127.0.0.1:8000"
USERNAME = "demo_user"
EMAIL = "demo@example.com"
PASSWORD = "SecurePass123"

# Imágenes a procesar
IMAGE_PATHS = [
    "../img/imagen1.png",
    "../img/imagen2.png",
    "../img/imagen3.png",
]


def signup_and_login():
    """Registra un usuario e inicia sesión."""
    print("📝 Registrando usuario...")
    signup_response = requests.post(
        f"{API_BASE}/signup",
        json={
            "username": USERNAME,
            "email": EMAIL,
            "password": PASSWORD
        }
    )
    
    if signup_response.status_code == 409:
        print("   Usuario ya existe, continuando con login...")
    elif signup_response.status_code == 200:
        print(f"   Usuario registrado: {signup_response.json()['username']}")
    else:
        raise Exception(f"Error en signup: {signup_response.text}")
    
    print("🔐 Iniciando sesión...")
    login_response = requests.post(
        f"{API_BASE}/login",
        json={
            "username": USERNAME,
            "password": PASSWORD
        }
    )
    
    if login_response.status_code != 200:
        raise Exception(f"Error en login: {login_response.text}")
    
    user_data = login_response.json()
    print(f"   Sesión iniciada: {user_data['username']} (ID: {user_data['usuario_id']})")
    return user_data['usuario_id']


def process_images_batch(usuario_id: int):
    """
    Procesa un lote de imágenes con transformaciones específicas.
    
    Ejemplo 1: Diferentes transformaciones por imagen usando 'instructions'
    Ejemplo 2: Mismas transformaciones para todas usando 'default_transforms'
    """
    
    print("\n🖼️  Preparando lote de imágenes...")
    
    # Definir transformaciones específicas para cada imagen
    instructions = [
        {
            "filename": "imagen1.png",
            "output_format": "jpg",
            "transforms": [
                {"code": "GRAYSCALE", "order": 1},
                {"code": "RESIZE", "params": {"width": 800, "height": 600}, "order": 2},
                {"code": "ROTATE", "params": {"degrees": 90}, "order": 3},
            ]
        },
        {
            "filename": "imagen2.png",
            "output_format": "png",
            "transforms": [
                {"code": "BLUR", "params": {"radius": 3.0}, "order": 1},
                {"code": "WATERMARK", "params": {"text": "Procesado", "x": 20, "y": 20}, "order": 2},
                {"code": "BRIGHTNESS_CONTRAST", "params": {"brightness": 1.2, "contrast": 1.1}, "order": 3},
            ]
        },
        {
            "filename": "imagen3.png",
            "output_format": "tif",
            "transforms": [
                {"code": "CROP", "params": {"x": 100, "y": 100, "width": 500, "height": 500}, "order": 1},
                {"code": "FLIP", "params": {"axis": "horizontal"}, "order": 2},
                {"code": "SHARPEN", "params": {"factor": 2.0}, "order": 3},
            ]
        },
    ]
    
    # Preparar archivos
    files = []
    for img_path in IMAGE_PATHS:
        path = Path(img_path)
        if path.exists():
            files.append(('files', (path.name, open(path, 'rb'), 'image/png')))
            print(f"   ✓ {path.name}")
        else:
            print(f"   ✗ No encontrado: {img_path}")
    
    if not files:
        raise Exception("No hay imágenes para procesar")
    
    # Preparar datos del formulario
    form_data = {
        'usuario_id': (None, str(usuario_id)),
        'output_format': (None, 'jpg'),
        'instructions': (None, json.dumps(instructions)),
    }
    
    print("\n⚙️  Enviando solicitud de procesamiento...")
    print(f"   Imágenes: {len(files)}")
    print(f"   Transformaciones por imagen: hasta 5")
    
    # Enviar solicitud
    response = requests.post(
        f"{API_BASE}/procesar-imagen",
        data=form_data,
        files=files
    )
    
    # Cerrar archivos
    for _, (_, file_obj, _) in files:
        file_obj.close()
    
    if response.status_code != 200:
        raise Exception(f"Error en procesamiento: {response.text}")
    
    # Guardar archivo ZIP
    output_filename = "imagenes_procesadas.zip"
    with open(output_filename, 'wb') as f:
        f.write(response.content)
    
    file_size_kb = len(response.content) / 1024
    print(f"\n✅ Proceso completado!")
    print(f"   Archivo ZIP: {output_filename}")
    print(f"   Tamaño: {file_size_kb:.2f} KB")
    
    return output_filename


def main():
    """Función principal."""
    print("=" * 60)
    print("  PROCESAMIENTO EN LOTE DE IMÁGENES CON TRANSFORMACIONES")
    print("=" * 60)
    
    try:
        # 1. Registro y login
        usuario_id = signup_and_login()
        
        # 2. Procesar imágenes
        zip_file = process_images_batch(usuario_id)
        
        print("\n" + "=" * 60)
        print(f"  ÉXITO: Imágenes procesadas guardadas en {zip_file}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
