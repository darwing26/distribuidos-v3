# backend/app.py
from fastapi import FastAPI
from pydantic import BaseModel
from .grpc_client import healthcheck, submit_job
from .models import log

app = FastAPI(title="Backend REST - Distribuidos IMG")

@app.get("/health/node")
def health(node: str):
    status, name = healthcheck(node)
    # Opcional: comentar si la DB aún no está lista
    log(f"Healthcheck {node} -> {status}/{name}")
    return {"node": node, "status": status, "name": name}

class ImageTransform(BaseModel):
    code: str
    params_json: str = "{}"
    order: int = 0

class ImageItem(BaseModel):
    image_id: int
    input_path: str
    output_format: str
    transforms: list[ImageTransform] = []

class SubmitBody(BaseModel):
    request_id: str
    node: str
    images: list[ImageItem]

@app.post("/jobs/submit")
def submit(body: SubmitBody):
    ack = submit_job(body.node, body.request_id, [im.dict() for im in body.images])
    log(f"Submit {body.request_id} -> {ack}")
    return {"ack": ack}

# Endpoint interno para progreso reportado por los nodos
class ProgressIn(BaseModel):
    imagen_id: int
    estado: str  # "procesada" | "error"
    ruta_salida: str | None = None
    error_msg: str | None = None

@app.post("/internal/progress")
def report_progress(p: ProgressIn):
    # Si ya implementaste estas funciones en models, impórtalas y úsalo:
    # from .models import actualizar_estado_imagen, actualizar_estado_solicitud, obtener_estado_solicitud
    try:
        from .models import actualizar_estado_imagen, log
        if p.estado == "procesada":
            actualizar_estado_imagen(p.imagen_id, "procesada", ruta_salida=p.ruta_salida)
        else:
            actualizar_estado_imagen(p.imagen_id, "error")
            log(f"Error imagen {p.imagen_id}: {p.error_msg}", nivel="ERROR", componente="backend")
    except Exception as e:
        # Si aún no tienes DB lista, al menos no rompas el endpoint
        print(f"[WARN] report_progress fallback: {e}")
    return {"ok": True}