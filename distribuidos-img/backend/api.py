# backend/api.py
import json
import os
import shutil
import uuid
import xml.etree.ElementTree as ET
import zipfile
from typing import Any, Dict, List

import bcrypt
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse
import httpx
from pydantic import BaseModel, EmailStr

from backend.models import (
  crear_usuario,
  obtener_usuario_por_email,
  obtener_usuario_por_id,
  obtener_usuario_por_username,
)

app = FastAPI(title="Frontend Cliente")

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
        if "x" in params:
            try:
                result["x"] = int(params["x"])
            except (TypeError, ValueError):
                raise ValueError("WATERMARK.x debe ser numérico")
        if "y" in params:
            try:
                result["y"] = int(params["y"])
            except (TypeError, ValueError):
                raise ValueError("WATERMARK.y debe ser numérico")
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
  if not validated:
    # Por defecto, escala de grises si no se especifica nada
    return [{"code": "GRAYSCALE", "params": {}, "order": 1}]
  return validated


def _parse_soap_response(xml_text: str) -> dict:
  root = ET.fromstring(xml_text)
  result = None
  for elem in root.iter():
    if elem.tag.endswith("crearSolicitudResult"):
      result = elem
      break
  if result is None or not result.text:
    raise ValueError("Respuesta SOAP sin cuerpo esperado")
  return json.loads(result.text)


class SignupBody(BaseModel):
  username: str
  email: EmailStr
  password: str


class LoginBody(BaseModel):
  username: str
  password: str


@app.post("/signup")
async def signup(body: SignupBody):
  username = body.username.strip()
  email = body.email.strip().lower()
  if not username:
    raise HTTPException(400, "El nombre de usuario no puede estar vacío")

  if obtener_usuario_por_username(username):
    raise HTTPException(409, "El nombre de usuario ya está registrado")

  if obtener_usuario_por_email(email):
    raise HTTPException(409, "El correo electrónico ya está registrado")

  if len(body.password) < 6:
    raise HTTPException(400, "La contraseña debe tener al menos 6 caracteres")

  pass_hash = bcrypt.hashpw(body.password.encode("utf-8"), bcrypt.gensalt()).decode()
  usuario_id = crear_usuario(username, email, pass_hash)
  return {"usuario_id": usuario_id, "username": username, "email": email}


@app.post("/login")
async def login(body: LoginBody):
  username = body.username.strip()
  user = obtener_usuario_por_username(username)
  if not user:
    raise HTTPException(401, "Credenciales inválidas")

  if user.get("estado") != "activo":
    raise HTTPException(403, "El usuario no está activo")

  stored = user.get("pass_hash", "")
  if not stored or not bcrypt.checkpw(body.password.encode("utf-8"), stored.encode("utf-8")):
    raise HTTPException(401, "Credenciales inválidas")

  return {
    "usuario_id": user["id"],
    "username": user["username"],
    "email": user["email"],
    "estado": user["estado"],
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

  os.makedirs("data/input", exist_ok=True)
  imagenes_payload: list[str] = []
  saved_paths: list[str] = []

  # Procesar cada imagen
  for index, upload in enumerate(uploads):
    if upload.filename is None:
      raise HTTPException(400, "Cada archivo debe tener un nombre válido")
    
    safe_name = upload.filename or "imagen"
    filename = f"{uuid.uuid4()}_{safe_name}"
    input_path = os.path.join("data", "input", filename)
    with open(input_path, "wb") as f:
      shutil.copyfileobj(upload.file, f)
    saved_paths.append(input_path)

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

    payload = json.dumps({
      "original_name": upload.filename,
      "input_path": input_path,
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
  
  # Esperar a que las imágenes estén listas (el worker ya las procesó sincrónicamente)
  if not os.path.exists(output_dir):
    raise HTTPException(500, "Las imágenes procesadas no están disponibles")

  # Crear archivo ZIP
  zip_filename = f"solicitud_{solicitud_id}.zip"
  zip_path = os.path.join("data", "output", zip_filename)
  
  try:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
      # Agregar todas las imágenes procesadas al ZIP
      for filename in os.listdir(output_dir):
        file_path = os.path.join(output_dir, filename)
        if os.path.isfile(file_path):
          zipf.write(file_path, arcname=filename)
    
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
