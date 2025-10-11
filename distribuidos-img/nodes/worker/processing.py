"""
Módulo de Procesamiento de Imágenes
====================================
Contiene toda la lógica para aplicar transformaciones a las imágenes.

Transformaciones soportadas:
- GRAYSCALE: Conversión a escala de grises
- RESIZE: Redimensionado con preservación de calidad
- CROP: Recorte de región específica
- ROTATE: Rotación con ángulo personalizado
- FLIP: Reflejo horizontal o vertical
- BLUR: Desenfoque gaussiano
- SHARPEN: Aumento de nitidez
- BRIGHTNESS_CONTRAST: Ajuste de brillo y contraste
- WATERMARK: Inserción de marca de agua/texto

Cada transformación es atómica y se aplican en secuencia según el orden especificado.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, Tuple

from PIL import Image, ImageOps, ImageFilter, ImageEnhance, ImageDraw, ImageFont

# Compatibilidad con diferentes versiones de Pillow
try:  # Pillow >= 9.1
    RESAMPLE_LANCZOS = Image.Resampling.LANCZOS
except AttributeError:  # Pillow < 9.1 (compatibilidad hacia atrás)
    RESAMPLE_LANCZOS = Image.LANCZOS


# ============================================
# Funciones auxiliares
# ============================================

def _load_params(params_raw: Any) -> Dict[str, Any]:
    """
    Parsea y normaliza los parámetros de una transformación.
    
    Los parámetros pueden venir en diferentes formatos:
    - Dict Python: Se retorna directamente
    - String JSON: Se parsea a dict
    - None/vacío: Se retorna dict vacío
    
    Args:
        params_raw: Parámetros en cualquier formato
        
    Returns:
        Dict con los parámetros parseados
    """
    if isinstance(params_raw, dict):
        return params_raw
    if not params_raw:
        return {}
    if isinstance(params_raw, str):
        try:
            return json.loads(params_raw)
        except json.JSONDecodeError:
            return {}
    return {}


def _resolve_save_format(fmt: str | None) -> str:
    """
    Convierte el formato de salida al nombre usado por PIL/Pillow.
    
    Args:
        fmt: Formato solicitado (jpg, png, tif, etc.)
        
    Returns:
        Formato normalizado para PIL (JPEG, PNG, TIFF, etc.)
    """
    fmt_norm = (fmt or "").strip().lower()
    mapping = {
        "jpg": "JPEG",
        "jpeg": "JPEG",
        "tif": "TIFF",
        "tiff": "TIFF",
        "bmp": "BMP",
    }
    return mapping.get(fmt_norm, fmt_norm.upper() or "JPEG")


# ============================================
# Aplicación de transformaciones individuales
# ============================================

def _apply_single_transform(img: Image.Image, code: str | None, params_raw: Any) -> Image.Image:
    """
    Aplica una única transformación a la imagen.
    
    Esta es la función核心 que implementa cada tipo de transformación.
    Cada transformación retorna una nueva imagen modificada.
    
    Args:
        img: Imagen PIL a transformar
        code: Código de la transformación (GRAYSCALE, RESIZE, etc.)
        params_raw: Parámetros específicos de la transformación
        
    Returns:
        Image.Image: Nueva imagen con la transformación aplicada
    """
    code = (code or "").strip().upper()
    params = _load_params(params_raw)

    # Sin transformación
    if code in {"", "NONE"}:
        return img

    # Convierte la imagen a escala de grises y la retorna en RGB
    if code == "GRAYSCALE":
        return ImageOps.grayscale(img).convert("RGB")

    # Redimensiona la imagen a las dimensiones especificadas
    if code == "RESIZE":
        width = int(params.get("width", img.width))
        height = int(params.get("height", img.height))
        # LANCZOS proporciona la mejor calidad en redimensionamiento
        return img.resize((width, height), RESAMPLE_LANCZOS)

    # Recorta una región rectangular de la imagen
    if code == "CROP":
        x = int(params.get("x", 0))
        y = int(params.get("y", 0))
        w = int(params.get("width", img.width - x))
        h = int(params.get("height", img.height - y))
        # crop() recibe (left, top, right, bottom)
        return img.crop((x, y, x + w, y + h))

    # Rota la imagen el número de grados especificado
    if code == "ROTATE":
        degrees = float(params.get("degrees", 0.0))
        # expand=True ajusta el tamaño para que quepa toda la imagen rotada
        return img.rotate(degrees, expand=True)

    # Refleja la imagen horizontal o verticalmente
    if code == "FLIP":
        axis = (params.get("axis", "horizontal")).lower()
        if axis == "vertical":
            return ImageOps.flip(img)  # Reflejo vertical
        return ImageOps.mirror(img)    # Reflejo horizontal

    # Aplica desenfoque gaussiano
    if code == "BLUR":
        radius = float(params.get("radius", 2.0))
        return img.filter(ImageFilter.GaussianBlur(radius))

    # Aumenta la nitidez de la imagen
    if code == "SHARPEN":
        factor = float(params.get("factor", 1.5))
        # factor > 1.0 aumenta nitidez, < 1.0 la reduce
        enhancer = ImageEnhance.Sharpness(img)
        return enhancer.enhance(factor)

    # Ajusta brillo y contraste
    if code == "BRIGHTNESS_CONTRAST":
        brightness = float(params.get("brightness", 1.0))
        contrast = float(params.get("contrast", 1.0))
        # 1.0 es el valor normal, >1.0 aumenta, <1.0 reduce
        img = ImageEnhance.Brightness(img).enhance(brightness)
        img = ImageEnhance.Contrast(img).enhance(contrast)
        return img

    # Inserta texto como marca de agua
    if code == "WATERMARK":
        text = str(params.get("text", "WM"))
        x = int(params.get("x", 10))
        y = int(params.get("y", 10))
        
        # Opciones adicionales con valores por defecto
        font_size = int(params.get("font_size", 40))  # Tamaño más visible por defecto
        color = params.get("color", "white")  # Color personalizable
        opacity = int(params.get("opacity", 180))  # Opacidad (0-255), más opaca por defecto
        
        # Convierte a RGBA para manejar transparencia
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        
        # Crea una capa transparente para el texto
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Intenta cargar una fuente TrueType más legible
        font = None
        try:
            # Intenta fuentes comunes en Windows
            for font_name in ["arial.ttf", "Arial.ttf", "verdana.ttf", "Verdana.ttf"]:
                try:
                    font = ImageFont.truetype(font_name, font_size)
                    break
                except:
                    continue
        except:
            pass
        
        # Si no encuentra fuente TrueType, usa la por defecto
        if font is None:
            try:
                font = ImageFont.load_default()
            except Exception:  # pragma: no cover
                font = None
        
        # Mapeo de colores con opacidad
        color_map = {
            "white": (255, 255, 255, opacity),
            "black": (0, 0, 0, opacity),
            "red": (255, 0, 0, opacity),
            "blue": (0, 0, 255, opacity),
            "green": (0, 255, 0, opacity),
            "yellow": (255, 255, 0, opacity),
            "cyan": (0, 255, 255, opacity),
            "magenta": (255, 0, 255, opacity),
            "orange": (255, 165, 0, opacity),
        }
        
        fill_color = color_map.get(color.lower(), (255, 255, 255, opacity))
        
        # Dibuja el texto con la fuente y color especificados
        draw.text((x, y), text, fill=fill_color, font=font)
        
        # Combina las capas y convierte de vuelta a RGB
        img = Image.alpha_composite(img, overlay).convert("RGB")
        return img

    # Si no reconoce la transformación, retorna la imagen sin cambios
    return img


# ============================================
# Función principal de procesamiento
# ============================================

def process_image_task(task, request_id: str) -> Tuple[str, str | None, str | None]:
    """
    Función principal que procesa una tarea de imagen completa.
    
    Esta función orquesta todo el proceso:
    1. Extrae información de la tarea (protobuf o dict)
    2. Crea directorios de salida
    3. Carga la imagen original
    4. Aplica todas las transformaciones en orden
    5. Guarda el resultado
    
    Args:
        task: ImageTask (protobuf) o diccionario con:
            - image_id: Identificador de la imagen
            - input_path: Ruta del archivo de entrada
            - output_format: Formato de salida (jpg, png, tif)
            - transforms: Lista de transformaciones ordenadas
        request_id: ID de la solicitud (para organizar outputs)
    
    Returns:
        Tuple[str, str | None, str | None]: (estado, ruta_salida, error)
            - estado: "ok" si exitoso, "error" si falló
            - ruta_salida: Path del archivo generado (si exitoso)
            - error: Mensaje de error (si falló)
    """

    # Paso 1: Extraer información de la tarea (compatible con protobuf y dict)
    if hasattr(task, "image_id"):
        # Es un objeto protobuf ImageTask
        image_id = task.image_id
        input_path = task.input_path
        output_format = (task.output_format or "jpg").lower()
        transforms = list(getattr(task, "transforms", []))
    else:
        # Es un diccionario
        image_id = task["image_id"]
        input_path = task["input_path"]
        output_format = str(task.get("output_format", "jpg")).lower()
        transforms = task.get("transforms", [])

    # Paso 2: Preparar rutas de salida
    # Organiza outputs por request_id: data/output/<request_id>/imagen.jpg
    output_dir = os.path.join("data", "output", str(request_id))
    os.makedirs(output_dir, exist_ok=True)
    
    # Conserva el nombre base del archivo, cambia la extensión
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    output_ext = "jpg" if output_format in {"jpeg"} else output_format
    output_path = os.path.join(output_dir, f"{base_name}.{output_ext}")

    try:
        # Paso 3: Cargar la imagen original
        img = Image.open(input_path)

        # Paso 4: Normalizar y ordenar transformaciones
        normalized: list[Tuple[int, str | None, Any]] = []
        for tr in transforms:
            if hasattr(tr, "order"):
                # Protobuf object
                order = int(getattr(tr, "order", 0))
                code = getattr(tr, "code", None)
                # Intentar obtener params de diferentes posibles nombres
                params = getattr(tr, "params_json", None) or getattr(tr, "params", None) or "{}"
                normalized.append((order, code, params))
            else:
                # Dictionary
                order = int(tr.get("order", 0))
                code = tr.get("code")
                params = tr.get("params_json", "{}") or tr.get("params", "{}")
                normalized.append((order, code, params))
        
        # Ordena por el campo 'order' para aplicar en secuencia correcta
        normalized = sorted(normalized, key=lambda x: x[0])

        # Debug: imprimir transformaciones para verificar
        print(f"[DEBUG] Procesando imagen {image_id} con {len(normalized)} transformaciones:")
        for order, code, params in normalized:
            print(f"  - Orden {order}: {code}")
            print(f"    Tipo de params: {type(params)}")
            print(f"    Valor raw: {params}")
            
            # Intenta parsear si es string
            if isinstance(params, str):
                try:
                    parsed = json.loads(params)
                    print(f"    Params parseados: {parsed}")
                except json.JSONDecodeError as e:
                    print(f"    ⚠️  Error al parsear JSON: {e}")

        # Paso 5: Aplicar transformaciones secuencialmente
        # Cada transformación modifica la imagen y la pasa a la siguiente
        for _, code, params in normalized:
            print(f"[DEBUG] Aplicando {code}...")
            img = _apply_single_transform(img, code, params)
            print(f"[DEBUG] {code} aplicada correctamente")

        # Paso 6: Preparar formato de guardado
        save_format = _resolve_save_format(output_format)
        
        # JPEG no soporta transparencia, convierte a RGB si es necesario
        if save_format == "JPEG" and img.mode not in {"RGB", "L"}:
            img = img.convert("RGB")
        
        # Guardar imagen procesada
        img.save(output_path, format=save_format)
        
        # Retorno exitoso
        return "ok", output_path, None
        
    except Exception as exc:  # pragma: no cover
        # Captura cualquier error (archivo no encontrado, formato inválido, etc.)
        return "error", None, str(exc)