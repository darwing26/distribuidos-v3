"""
Script para crear imágenes de prueba
"""
from PIL import Image, ImageDraw, ImageFont
import os

# Crear carpeta si no existe
os.makedirs("data/input", exist_ok=True)

# Crear 3 imágenes de prueba con diferentes colores
colors = [
    ("test_imagen1.png", (255, 0, 0)),      # Roja
    ("test_imagen2.png", (0, 255, 0)),      # Verde
    ("test_imagen3.png", (0, 0, 255)),      # Azul
]

for filename, color in colors:
    # Crear imagen 400x300
    img = Image.new('RGB', (400, 300), color)
    draw = ImageDraw.Draw(img)
    
    # Agregar texto
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        font = ImageFont.load_default()
    
    text = f"Imagen {filename[12]}"  # Extraer el número
    
    # Calcular posición centrada
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    position = ((400 - text_width) // 2, (300 - text_height) // 2)
    
    # Dibujar texto en blanco
    draw.text(position, text, fill=(255, 255, 255), font=font)
    
    # Guardar
    filepath = os.path.join("data/input", filename)
    img.save(filepath)
    print(f"✅ Creada: {filepath}")

print("\n🎉 ¡Imágenes de prueba creadas exitosamente!")
