"""Módulo con rutinas de procesamiento de imágenes para los nodos worker."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, Tuple

from PIL import Image, ImageOps, ImageFilter, ImageEnhance, ImageDraw, ImageFont

try:  # Compatibilidad con Pillow < 9.1
    RESAMPLE_LANCZOS = Image.Resampling.LANCZOS
except AttributeError:  # pragma: no cover
    RESAMPLE_LANCZOS = Image.LANCZOS


def _load_params(params_raw: Any) -> Dict[str, Any]:
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


def _apply_single_transform(img: Image.Image, code: str | None, params_raw: Any) -> Image.Image:
    code = (code or "").strip().upper()
    params = _load_params(params_raw)

    if code in {"", "NONE"}:
        return img

    if code == "GRAYSCALE":
        return ImageOps.grayscale(img).convert("RGB")

    if code == "RESIZE":
        width = int(params.get("width", img.width))
        height = int(params.get("height", img.height))
    return img.resize((width, height), RESAMPLE_LANCZOS)

    if code == "CROP":
        x = int(params.get("x", 0))
        y = int(params.get("y", 0))
        w = int(params.get("width", img.width - x))
        h = int(params.get("height", img.height - y))
        return img.crop((x, y, x + w, y + h))

    if code == "ROTATE":
        degrees = float(params.get("degrees", 0.0))
        return img.rotate(degrees, expand=True)

    if code == "FLIP":
        axis = (params.get("axis", "horizontal")).lower()
        if axis == "vertical":
            return ImageOps.flip(img)
        return ImageOps.mirror(img)

    if code == "BLUR":
        radius = float(params.get("radius", 2.0))
        return img.filter(ImageFilter.GaussianBlur(radius))

    if code == "SHARPEN":
        factor = float(params.get("factor", 1.5))
        enhancer = ImageEnhance.Sharpness(img)
        return enhancer.enhance(factor)

    if code == "BRIGHTNESS_CONTRAST":
        brightness = float(params.get("brightness", 1.0))
        contrast = float(params.get("contrast", 1.0))
        img = ImageEnhance.Brightness(img).enhance(brightness)
        img = ImageEnhance.Contrast(img).enhance(contrast)
        return img

    if code == "WATERMARK":
        text = str(params.get("text", "WM"))
        x = int(params.get("x", 10))
        y = int(params.get("y", 10))
        img = img.convert("RGBA")
        overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)
        try:
            font = ImageFont.load_default()
        except Exception:  # pragma: no cover
            font = None
        draw.text((x, y), text, fill=(255, 255, 255, 128), font=font)
        img = Image.alpha_composite(img, overlay).convert("RGB")
        return img

    return img


def process_image_task(task, request_id: str) -> Tuple[str, str | None, str | None]:
    """Procesa una imagen y devuelve ``(estado, ruta_salida, error)``.

    ``task`` puede ser un objeto protobuf ``ImageTask`` o un diccionario con las
    mismas claves. La ruta de salida se crea bajo ``data/output/<request_id>``.
    """

    if hasattr(task, "image_id"):
        image_id = task.image_id
        input_path = task.input_path
        output_format = (task.output_format or "jpg").lower()
        transforms = list(getattr(task, "transforms", []))
    else:
        image_id = task["image_id"]
        input_path = task["input_path"]
        output_format = str(task.get("output_format", "jpg")).lower()
        transforms = task.get("transforms", [])

    output_dir = os.path.join("data", "output", str(request_id))
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}.{output_format}")

    try:
        img = Image.open(input_path)

        normalized: list[Tuple[int, str | None, Any]] = []
        tmp: list[Tuple[int, str | None, Any]] = []
        for tr in transforms:
            if hasattr(tr, "order"):
                tmp.append((int(getattr(tr, "order", 0)), getattr(tr, "code", None), getattr(tr, "params_json", "{}")))
            else:
                tmp.append((int(tr.get("order", 0)), tr.get("code"), tr.get("params_json", "{}")))
        normalized = sorted(tmp, key=lambda x: x[0])

        if not tmp:
            normalized = [(0, "GRAYSCALE", "{}")]

        for _, code, params in normalized:
            img = _apply_single_transform(img, code, params)

        img.save(output_path, format=output_format.upper())
        return "ok", output_path, None
    except Exception as exc:  # pragma: no cover
        return "error", None, str(exc)