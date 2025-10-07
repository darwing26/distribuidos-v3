# backend/api.py
import json
import os
import shutil
import uuid
import xml.etree.ElementTree as ET

import bcrypt
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
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


def soap_envelope(body_xml: str) -> str:
  return f"""<?xml version="1.0" encoding="utf-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="{SOAP_NS}">
  <soapenv:Header/>
  <soapenv:Body>{body_xml}</soapenv:Body>
</soapenv:Envelope>"""


def _build_transforms(transforms_json: str | None) -> list[dict]:
  if not transforms_json:
    return [{"code": "GRAYSCALE", "params": {}, "order": 1}]
  data = json.loads(transforms_json)
  if not isinstance(data, list):
    raise ValueError("transforms debe ser una lista de objetos")
  transforms = []
  for idx, item in enumerate(data, start=1):
    if not isinstance(item, dict):
      raise ValueError("Cada transform debe ser un objeto")
    code = str(item.get("code", "")).upper()
    params = item.get("params", {})
    transforms.append({
      "code": code,
      "params": params if isinstance(params, dict) else {},
      "order": item.get("order", idx),
    })
  return transforms


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
  transforms: str | None = Form(None),
  files: List[UploadFile] = File(...),
):
  usuario = obtener_usuario_por_id(usuario_id)
  if not usuario:
    raise HTTPException(404, "Usuario no encontrado")
  if usuario.get("estado") != "activo":
    raise HTTPException(403, "Usuario inactivo o bloqueado")

  uploads = list(files or [])
  if not uploads:
    raise HTTPException(400, "Debe adjuntar al menos una imagen")

  os.makedirs("data/input", exist_ok=True)
  transforms_list = _build_transforms(transforms)
  imagenes_payload: list[str] = []
  saved_paths: list[str] = []

  for upload in uploads:
    if upload.filename is None:
      raise HTTPException(400, "Cada archivo debe tener un nombre válido")
    safe_name = upload.filename or "imagen"
    filename = f"{uuid.uuid4()}_{safe_name}"
    input_path = os.path.join("data", "input", filename)
    with open(input_path, "wb") as f:
      shutil.copyfileobj(upload.file, f)
    saved_paths.append(input_path)

    payload = json.dumps({
      "original_name": upload.filename,
      "input_path": input_path,
      "input_format": upload.filename.split(".")[-1] if "." in upload.filename else "jpg",
      "output_format": output_format,
      "transforms": transforms_list,
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
  async with httpx.AsyncClient(timeout=60.0) as client:
    resp = await client.post(SOAP_URL, content=xml, headers=headers)

  if resp.status_code != 200:
    raise HTTPException(502, f"SOAP error: {resp.text}")

  try:
    ack = _parse_soap_response(resp.text)
  except Exception as exc:  # pragma: no cover
    raise HTTPException(502, f"Respuesta SOAP inválida: {exc}") from exc

  return {"solicitud": ack, "input_paths": saved_paths}
