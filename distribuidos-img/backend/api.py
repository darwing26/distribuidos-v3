# backend/api.py
"""
Backend API - Servidor de Lógica de Negocio
============================================
Este es el servidor backend que maneja la lógica de negocio y se comunica con SOAP.
El Frontend se comunica con este servidor vía REST API.

Responsabilidades:
- Validar usuarios
- Gestionar archivos de imágenes
- Comunicación con servicio SOAP
- Crear y retornar archivos ZIP procesados
"""

import base64
import json
import os
import shutil
import time
import uuid
import xml.etree.ElementTree as ET
import zipfile
from typing import Any, Dict, List

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse
import httpx
from pydantic import BaseModel, EmailStr

from backend.models import (
  obtener_usuario_por_id,
)

app = FastAPI(
    title="Backend API",
    description="Servidor backend que maneja procesamiento de imágenes",
    version="2.0.0"
)

SOAP_URL = "http://127.0.0.1:9000/"
SOAP_NS = "svc.imagenes"

# Transformaciones permitidas (máximo 5 por imagen)
ALLOWED_TRANSFORMS = {
    "GRAYSCALE",      # Conversión a escala de grises
    "RESIZE",         # Redimensionar
    "CROP",           # Recortar
    "ROTATE",         # Rotar
    "FLIP",           # Reflejar
    "BLUR",           # Desenfocar
    "SHARPEN",        # Perfilar (nitidez)
    "BRIGHTNESS_CONTRAST",  # Ajuste de brillo y contraste
    "WATERMARK",      # Inserción de marcas de agua o texto
}

# Formatos de salida permitidos
ALLOWED_FORMATS = {"jpg", "png", "tif"}


def _validate_transform_params(code: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Valida y normaliza los parámetros de cada transformación."""
    code = code.upper()
    
    if code == "GRAYSCALE":
        return {}
    
    if code == "RESIZE":
        try:
            width = int(params.get("width", 0))
            height = int(params.get("height", 0))
            if width <= 0 or height <= 0:
                raise ValueError("RESIZE requiere width y height positivos")
            return {"width": width, "height": height}
        except (TypeError, ValueError) as exc:
            raise ValueError(f"RESIZE requiere parámetros width y height válidos: {exc}")
    
    if code == "CROP":
        try:
            x = int(params.get("x", 0))
            y = int(params.get("y", 0))
            width = int(params.get("width", 0))
            height = int(params.get("height", 0))
            if width <= 0 or height <= 0:
                raise ValueError("CROP requiere width y height positivos")
            return {"x": x, "y": y, "width": width, "height": height}
        except (TypeError, ValueError) as exc:
            raise ValueError(f"CROP requiere parámetros x, y, width, height válidos: {exc}")
    
    if code == "ROTATE":
        try:
            degrees = float(params.get("degrees", 0))
            return {"degrees": degrees}
        except (TypeError, ValueError) as exc:
            raise ValueError(f"ROTATE requiere parámetro degrees válido: {exc}")
    
    if code == "FLIP":
        axis = str(params.get("axis", "horizontal")).lower()
        if axis not in {"horizontal", "vertical"}:
            raise ValueError("FLIP requiere axis 'horizontal' o 'vertical'")
        return {"axis": axis}
    
    if code == "BLUR":
        try:
            radius = float(params.get("radius", 2.0))
            if radius <= 0:
                raise ValueError("BLUR requiere radius positivo")
            return {"radius": radius}
        except (TypeError, ValueError) as exc:
            raise ValueError(f"BLUR requiere parámetro radius válido: {exc}")
    
    if code == "SHARPEN":
        try:
            factor = float(params.get("factor", 1.5))
            if factor <= 0:
                raise ValueError("SHARPEN requiere factor positivo")
            return {"factor": factor}
        except (TypeError, ValueError) as exc:
            raise ValueError(f"SHARPEN requiere parámetro factor válido: {exc}")
    
    if code == "BRIGHTNESS_CONTRAST":
        try:
            brightness = float(params.get("brightness", 1.0))
            contrast = float(params.get("contrast", 1.0))
            return {"brightness": brightness, "contrast": contrast}
        except (TypeError, ValueError) as exc:
            raise ValueError(f"BRIGHTNESS_CONTRAST requiere parámetros brightness y contrast válidos: {exc}")
    
    if code == "WATERMARK":
        text = str(params.get("text", "")).strip()
        if not text:
            raise ValueError("WATERMARK requiere el parámetro 'text'")
        result = {"text": text}
        
        # Validar posición X
        if "x" in params:
            try:
                result["x"] = int(params["x"])
            except (TypeError, ValueError):
                raise ValueError("WATERMARK.x debe ser numérico")
        
        # Validar posición Y
        if "y" in params:
            try:
                result["y"] = int(params["y"])
            except (TypeError, ValueError):
                raise ValueError("WATERMARK.y debe ser numérico")
        
        # Validar tamaño de fuente (opcional)
        if "font_size" in params:
            try:
                font_size = int(params["font_size"])
                if font_size < 8 or font_size > 200:
                    raise ValueError("font_size debe estar entre 8 y 200")
                result["font_size"] = font_size
            except (TypeError, ValueError) as e:
                raise ValueError(f"WATERMARK.font_size inválido: {e}")
        
        # Validar color (opcional)
        if "color" in params:
            color = str(params["color"]).lower()
            allowed_colors = {"white", "black", "red", "blue", "green", "yellow", "cyan", "magenta", "orange"}
            if color not in allowed_colors:
                raise ValueError(f"WATERMARK.color debe ser uno de: {', '.join(allowed_colors)}")
            result["color"] = color
        
        # Validar opacidad (opcional)
        if "opacity" in params:
            try:
                opacity = int(params["opacity"])
                if opacity < 0 or opacity > 255:
                    raise ValueError("opacity debe estar entre 0 y 255")
                result["opacity"] = opacity
            except (TypeError, ValueError) as e:
                raise ValueError(f"WATERMARK.opacity inválido: {e}")
        
        return result
    
    return params


def _validate_transforms(transforms_data: Any, max_transforms: int = 5) -> List[dict]:
    """
    Valida que las transformaciones sean correctas y no excedan el límite.
    Retorna una lista normalizada de transformaciones.
    """
    if transforms_data is None or transforms_data == "":
        return []
    
    # Si es string, intentar parsear como JSON
    if isinstance(transforms_data, str):
        try:
            transforms_data = json.loads(transforms_data)
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON de transformaciones inválido: {exc}")
    
    if not isinstance(transforms_data, list):
        raise ValueError("Las transformaciones deben ser una lista")
    
    if len(transforms_data) > max_transforms:
        raise ValueError(f"Máximo {max_transforms} transformaciones permitidas por imagen")
    
    normalized = []
    for idx, item in enumerate(transforms_data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Transformación #{idx} debe ser un objeto")
        
        code = str(item.get("code", "")).upper()
        if not code:
            raise ValueError(f"Transformación #{idx} debe tener un código")
        
        if code not in ALLOWED_TRANSFORMS:
            raise ValueError(f"Transformación no soportada: {code}")
        
        params_raw = item.get("params", {})
        if not isinstance(params_raw, dict):
            params_raw = {}
        
        # Validar y normalizar parámetros
        params = _validate_transform_params(code, params_raw)
        
        normalized.append({
            "code": code,
            "params": params,
            "order": item.get("order", idx)
        })
    
    return normalized


def soap_envelope(body_xml: str) -> str:
  return f"""<?xml version="1.0" encoding="utf-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="{SOAP_NS}">
  <soapenv:Header/>
  <soapenv:Body>{body_xml}</soapenv:Body>
</soapenv:Envelope>"""


def _build_transforms(transforms_json: str | None) -> list[dict]:
  """Construye lista de transformaciones, aplicando validación."""
  validated = _validate_transforms(transforms_json)
  # Si no hay transformaciones, retornar lista vacía (no aplicar nada)
  return validated


def _parse_soap_response(xml_text: str) -> dict:
  """Parsea la respuesta SOAP y extrae el resultado JSON"""
  root = ET.fromstring(xml_text)
  result = None
  for elem in root.iter():
    if elem.tag.endswith("crearSolicitudResult"):
      result = elem
      break
  if result is None or not result.text:
    raise ValueError("Respuesta SOAP sin cuerpo esperado")
  return json.loads(result.text)


# =============================================================================
# ENDPOINTS DEL BACKEND
# =============================================================================

@app.get("/")
async def root():
  """
  Endpoint raíz - Información del servicio backend
  """
  return {
    "service": "Backend API",
    "version": "2.0.0",
    "description": "Servidor backend para procesamiento de imágenes",
    "soap_url": SOAP_URL
  }


@app.get("/health")
async def health_check():
  """
  Health check del backend
  Verifica conexión con el servicio SOAP
  """
  try:
    async with httpx.AsyncClient(timeout=5.0) as client:
      # Intentar conectar con SOAP
      resp = await client.get(SOAP_URL.rstrip("/") + "/?wsdl")
      soap_status = "ok" if resp.status_code == 200 else "error"
  except:
    soap_status = "unreachable"
  
  return {
    "status": "ok",
    "soap_service": soap_status,
    "soap_url": SOAP_URL
  }


@app.post("/procesar-imagen")
async def procesar_imagen(
  usuario_id: int = Form(...),
  output_format: str = Form("jpg"),
  default_transforms: str | None = Form(None),
  instructions: str | None = Form(None),
  files: List[UploadFile] = File(...),
):
  """
  Procesa un lote de imágenes con transformaciones específicas por imagen.
  
  Parámetros:
  - usuario_id: ID del usuario autenticado
  - output_format: Formato de salida por defecto (jpg, png, tif)
  - default_transforms: Transformaciones por defecto (JSON) aplicadas a todas las imágenes
  - instructions: Lista JSON con instrucciones específicas por imagen
  - files: Archivos de imagen a procesar
  
  Retorna un archivo ZIP con todas las imágenes procesadas.
  """
  usuario = obtener_usuario_por_id(usuario_id)
  if not usuario:
    raise HTTPException(404, "Usuario no encontrado")
  if usuario.get("estado") != "activo":
    raise HTTPException(403, "Usuario inactivo o bloqueado")

  uploads = list(files or [])
  if not uploads:
    raise HTTPException(400, "Debe adjuntar al menos una imagen")

  # Validar formato de salida
  output_format = output_format.strip().lower()
  if output_format not in ALLOWED_FORMATS:
    raise HTTPException(400, f"Formato de salida debe ser uno de: {', '.join(ALLOWED_FORMATS)}")

  # Parsear transformaciones por defecto
  try:
    default_transforms_list = _build_transforms(default_transforms)
  except ValueError as exc:
    raise HTTPException(400, f"Transformaciones por defecto inválidas: {exc}")

  # Parsear instrucciones específicas por imagen
  instructions_data: List[dict] = []
  if instructions:
    try:
      parsed = json.loads(instructions)
      if not isinstance(parsed, list):
        raise HTTPException(400, "Las instrucciones deben ser una lista")
      instructions_data = parsed
    except json.JSONDecodeError as exc:
      raise HTTPException(400, f"JSON de instrucciones inválido: {exc}")

  # Crear índice de instrucciones por nombre de archivo
  instructions_by_filename: Dict[str, dict] = {}
  instructions_by_index: Dict[int, dict] = {}
  for idx, item in enumerate(instructions_data):
    if not isinstance(item, dict):
      raise HTTPException(400, f"Instrucción #{idx+1} debe ser un objeto")
    filename = item.get("filename")
    if filename:
      instructions_by_filename[str(filename)] = item
    instructions_by_index[idx] = item

  imagenes_payload: list[str] = []

  # Procesar cada imagen
  for index, upload in enumerate(uploads):
    if upload.filename is None:
      raise HTTPException(400, "Cada archivo debe tener un nombre válido")
    
    # Leer el contenido de la imagen y convertir a base64
    image_bytes = await upload.read()
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    
    # Generar un ID único para esta imagen
    imagen_id = str(uuid.uuid4())

    # Obtener instrucciones específicas para esta imagen
    instruction = instructions_by_filename.get(upload.filename) or instructions_by_index.get(index)

    # Determinar transformaciones para esta imagen
    if instruction and "transforms" in instruction:
      try:
        image_transforms = _validate_transforms(instruction["transforms"])
      except ValueError as exc:
        raise HTTPException(400, f"Transformaciones inválidas para {upload.filename}: {exc}")
    else:
      # Usar transformaciones por defecto
      image_transforms = [dict(t) for t in default_transforms_list]

    # Determinar formato de salida para esta imagen
    if instruction and "output_format" in instruction:
      image_output_format = str(instruction["output_format"]).strip().lower()
      if image_output_format not in ALLOWED_FORMATS:
        raise HTTPException(400, f"Formato inválido para {upload.filename}: {image_output_format}")
    else:
      image_output_format = output_format

    # Crear payload con imagen en base64
    payload = json.dumps({
      "imagen_id": imagen_id,
      "original_name": upload.filename,
      "image_data": image_base64,
      "input_format": upload.filename.split(".")[-1] if "." in upload.filename else "jpg",
      "output_format": image_output_format,
      "transforms": image_transforms,
    })
    imagenes_payload.append(f"<tns:string><![CDATA[{payload}]]></tns:string>")

  body = f"""
  <tns:crearSolicitud>
    <tns:usuario_id>{usuario_id}</tns:usuario_id>
    <tns:imagenes>
    {''.join(imagenes_payload)}
    </tns:imagenes>
  </tns:crearSolicitud>
  """
  xml = soap_envelope(body)

  headers = {"Content-Type": "text/xml; charset=utf-8"}
  async with httpx.AsyncClient(timeout=120.0) as client:
    resp = await client.post(SOAP_URL, content=xml, headers=headers)

  if resp.status_code != 200:
    raise HTTPException(502, f"SOAP error: {resp.text}")

  try:
    ack = _parse_soap_response(resp.text)
  except Exception as exc:  # pragma: no cover
    raise HTTPException(502, f"Respuesta SOAP inválida: {exc}") from exc

  # Crear archivo ZIP con las imágenes procesadas
  solicitud_id = ack.get("solicitud_id")
  if not solicitud_id:
    raise HTTPException(500, "No se pudo obtener el ID de la solicitud")

  # Directorio donde están las imágenes procesadas
  output_dir = os.path.join("data", "output", str(solicitud_id))
  
  # Dar un tiempo razonable para que el worker termine de procesar
  max_wait = 30  # segundos
  wait_interval = 0.5  # segundos
  elapsed = 0
  
  while not os.path.exists(output_dir) and elapsed < max_wait:
    time.sleep(wait_interval)
    elapsed += wait_interval
  
  # Verificar que el directorio existe y tiene archivos
  if not os.path.exists(output_dir):
    raise HTTPException(500, f"Las imágenes procesadas no están disponibles. Directorio esperado: {output_dir}")
  
  # Verificar que hay archivos en el directorio
  archivos = [f for f in os.listdir(output_dir) if os.path.isfile(os.path.join(output_dir, f))]
  if not archivos:
    raise HTTPException(500, f"No se encontraron imágenes procesadas en {output_dir}")
  
  # Crear archivo ZIP con todas las imágenes en una carpeta con el ID de la solicitud
  zip_filename = f"solicitud_{solicitud_id}.zip"
  zip_path = os.path.join("data", "output", zip_filename)
  
  try:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
      # Agregar todas las imágenes procesadas al ZIP dentro de una carpeta
      # con el nombre del ID de la solicitud
      for filename in archivos:
        file_path = os.path.join(output_dir, filename)
        # arcname incluye la carpeta con el ID de la solicitud
        arcname = f"solicitud_{solicitud_id}/{filename}"
        zipf.write(file_path, arcname=arcname)
    
    print(f"[INFO] ZIP creado exitosamente: {zip_path} con {len(archivos)} archivo(s)")
    
    # Retornar el archivo ZIP
    return FileResponse(
      path=zip_path,
      media_type="application/zip",
      filename=zip_filename,
      headers={
        "Content-Disposition": f"attachment; filename={zip_filename}"
      }
    )
  except Exception as exc:
    raise HTTPException(500, f"Error al crear archivo ZIP: {exc}")
