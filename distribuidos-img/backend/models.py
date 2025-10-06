# backend/models.py
"""Funciones de acceso a datos para usuarios, solicitudes, imágenes y nodos."""

from __future__ import annotations

import os
from typing import Optional

import pymysql

from backend.db import get_conn


def crear_usuario(username: str, email: str, pass_hash: str, estado: str = "activo") -> int:
    """Registra un nuevo usuario y devuelve su ID."""

    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO usuarios (username, email, pass_hash, estado)
            VALUES (%s, %s, %s, %s)
            """,
            (username, email, pass_hash, estado),
        )
        usuario_id = cur.lastrowid
        conn.commit()
        return usuario_id
    finally:
        cur.close(); conn.close()


def obtener_usuario_por_username(username: str) -> Optional[dict]:
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM usuarios WHERE username=%s", (username,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row


def obtener_usuario_por_email(email: str) -> Optional[dict]:
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM usuarios WHERE email=%s", (email,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row


def obtener_usuario_por_id(usuario_id: int) -> Optional[dict]:
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM usuarios WHERE id=%s", (usuario_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row

def crear_solicitud(usuario_id: int, total_imagenes: int) -> int:
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO solicitudes (usuario_id, estado, total_imagenes, creadas_en, actualizadas_en)
        VALUES (%s, 'pendiente', %s, NOW(), NOW())
    """, (usuario_id, total_imagenes))
    solicitud_id = cur.lastrowid
    conn.commit(); cur.close(); conn.close()
    return solicitud_id

def _normalizar_formato_origen(formato: str | None) -> str:
    permitido = {"jpg", "jpeg", "png", "tif", "tiff", "bmp", "gif", "webp"}
    fmt = (formato or "").strip().lower()
    if fmt in permitido:
        return fmt
    if fmt in {"jpg", "jpeg"}:
        return "jpg"
    if fmt in {"tif", "tiff"}:
        return "tif"
    return "otro"


def _normalizar_formato_salida(formato: str | None) -> str:
    fmt = (formato or "").strip().lower()
    if fmt in {"jpg", "png", "tif"}:
        return fmt
    if fmt in {"jpeg"}:
        return "jpg"
    if fmt in {"tiff"}:
        return "tif"
    return "sin_cambio"


def _sanear_nombre(nombre: str | None, solicitud_id: int) -> str:
    base = (nombre or "").strip()
    if not base:
        base = f"imagen_{solicitud_id}"
    base_name = os.path.basename(base)
    sin_ext, ext = os.path.splitext(base_name)
    sin_ext = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in sin_ext) or f"imagen_{solicitud_id}"
    ext = ext.lower()
    return f"{sin_ext}{ext}" if ext else sin_ext


def _normalizar_estado_imagen(estado: str | None) -> str:
    estado = (estado or "").strip().lower()
    mapping = {
        "ok": "completada",
        "success": "completada",
        "procesada": "completada",
        "completada": "completada",
        "completed": "completada",
        "error": "fallida",
        "fail": "fallida",
        "failed": "fallida",
        "fallida": "fallida",
        "con_error": "fallida",
        "processing": "en_progreso",
        "in_progress": "en_progreso",
        "pendiente": "pendiente",
    }
    return mapping.get(estado, "pendiente")


def _normalizar_estado_solicitud(estado: str | None) -> str:
    estado = (estado or "").strip().lower()
    mapping = {
        "ok": "completada",
        "completada": "completada",
        "success": "completada",
        "con_error": "fallida",
        "error": "fallida",
        "fallida": "fallida",
        "fail": "fallida",
        "procesando": "en_progreso",
        "processing": "en_progreso",
        "pendiente": "pendiente",
        "cancelada": "cancelada",
    }
    return mapping.get(estado, "pendiente")


def registrar_imagen(solicitud_id: int, nombre: str, ruta_entrada: str, formato_entrada: str, formato_salida: str) -> int:
    conn = get_conn(); cur = conn.cursor()
    nombre_original = nombre or os.path.basename(ruta_entrada)
    nombre_registro = _sanear_nombre(nombre_original, solicitud_id)

    formato_in = (formato_entrada or "").strip().lower()
    formato_sal = (formato_salida or "").strip().lower()
    formato_origen = _normalizar_formato_origen(formato_in)
    formato_entrada_norm = formato_in or formato_origen or "jpg"
    formato_salida_norm = _normalizar_formato_salida(formato_sal)

    sql_extendido = """
        INSERT INTO imagenes (
            solicitud_id,
            nombre,
            nombre_original,
            ruta_entrada,
            formato_entrada,
            formato_salida,
            formato_origen,
            estado,
            creada_en,
            actualizada_en
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,'pendiente',NOW(),NOW())
    """
    params_ext = (
        solicitud_id,
        nombre_registro,
        nombre_original,
        ruta_entrada,
        formato_entrada_norm,
        formato_salida_norm,
        formato_origen,
    )

    try:
        cur.execute(sql_extendido, params_ext)
    except (pymysql.err.OperationalError, pymysql.err.ProgrammingError):
        cur.execute(
            """
                INSERT INTO imagenes (solicitud_id, nombre, ruta_entrada, formato_entrada, formato_salida, estado, creada_en, actualizada_en)
                VALUES (%s,%s,%s,%s,%s,'pendiente',NOW(),NOW())
            """,
            (solicitud_id, nombre_registro, ruta_entrada, formato_entrada_norm, formato_salida_norm),
        )

    imagen_id = cur.lastrowid
    conn.commit(); cur.close(); conn.close()
    return imagen_id

def agregar_transformacion(imagen_id: int, codigo: str, orden: int, params_json: str):
    conn = get_conn(); cur = conn.cursor()
    codigo = (codigo or "").strip()
    params_json = params_json or "{}"
    codigo_lower = codigo.lower() or "custom"

    transformacion_id = None
    try:
        cur.execute("SELECT id FROM transformaciones WHERE codigo=%s", (codigo_lower,))
        row = cur.fetchone()
        if row:
            transformacion_id = row["id"]
        else:
            cur.execute(
                "INSERT INTO transformaciones (codigo, descripcion) VALUES (%s,%s)",
                (codigo_lower, codigo.replace("_", " ").title() or codigo_lower),
            )
            transformacion_id = cur.lastrowid
    except (pymysql.err.OperationalError, pymysql.err.ProgrammingError):
        transformacion_id = None

    try:
        cur.execute(
            """
                INSERT INTO imagen_transformaciones (
                    imagen_id,
                    transformacion_id,
                    codigo,
                    orden,
                    parametros,
                    params_json,
                    creado_en,
                    creada_en
                ) VALUES (%s,%s,%s,%s,%s,%s,NOW(),NOW())
            """,
            (imagen_id, transformacion_id, codigo_lower, orden, params_json, params_json),
        )
    except (pymysql.err.OperationalError, pymysql.err.ProgrammingError):
        cur.execute(
            """
                INSERT INTO imagen_transformaciones (imagen_id, codigo, orden, params_json, creada_en)
                VALUES (%s,%s,%s,%s,NOW())
            """,
            (imagen_id, codigo, orden, params_json),
        )

    conn.commit(); cur.close(); conn.close()

def obtener_nodos_activos():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT id, nombre, direccion FROM nodos WHERE estado='activo'")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def registrar_nodo(nombre: str, direccion: str, protocolo: str = "grpc", estado: str = "activo"):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO nodos (nombre, direccion, protocolo, estado, ultima_actividad)
        VALUES (%s,%s,%s,%s,NOW())
        ON DUPLICATE KEY UPDATE
            direccion=VALUES(direccion),
            protocolo=VALUES(protocolo),
            estado=VALUES(estado),
            ultima_actividad=NOW()
    """, (nombre, direccion, protocolo, estado))
    conn.commit(); cur.close(); conn.close()

def actualizar_estado_imagen(imagen_id: int, estado: str, nodo_id=None, ruta_salida=None, mensaje_error=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        estado_db = _normalizar_estado_imagen(estado)
        cur.execute("""
            UPDATE imagenes
               SET estado=%s,
                   nodo_id=%s,
                   ruta_salida=COALESCE(%s, ruta_salida),
                   mensaje_error=%s,
                   actualizada_en=NOW()
             WHERE id=%s
        """, (estado_db, nodo_id, ruta_salida, mensaje_error, imagen_id))
    except Exception:
        estado_db = _normalizar_estado_imagen(estado)
        # Fallback si la columna mensaje_error no existe.
        cur.execute("""
            UPDATE imagenes
               SET estado=%s,
                   nodo_id=%s,
                   ruta_salida=COALESCE(%s, ruta_salida),
                   actualizada_en=NOW()
             WHERE id=%s
        """, (estado_db, nodo_id, ruta_salida, imagen_id))
    conn.commit(); cur.close(); conn.close()

def actualizar_estado_solicitud(solicitud_id: int, estado: str):
    conn = get_conn(); cur = conn.cursor()
    estado_db = _normalizar_estado_solicitud(estado)
    cur.execute("""
        UPDATE solicitudes SET estado=%s, actualizadas_en=NOW() WHERE id=%s
    """, (estado_db, solicitud_id))
    conn.commit(); cur.close(); conn.close()

def obtener_estado_solicitud(solicitud_id: int):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT id, usuario_id, estado FROM solicitudes WHERE id=%s", (solicitud_id,))
    sol = cur.fetchone()
    cur.execute("SELECT id, nombre, estado FROM imagenes WHERE solicitud_id=%s", (solicitud_id,))
    imgs = cur.fetchall()
    cur.close(); conn.close()
    return sol, imgs

def log(mensaje: str, nivel="INFO", componente="app", solicitud_id=None):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO logs (nivel, componente, mensaje, solicitud_id, creado_en)
        VALUES (%s,%s,%s,%s,NOW())
    """, (nivel, componente, mensaje, solicitud_id))
    conn.commit(); cur.close(); conn.close()