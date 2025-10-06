#!/usr/bin/env bash
# Usage: ./init.sh [project_name]
# Crea la estructura del proyecto (backend y nodos) lista para el Avance 2.

set -euo pipefail

PROJECT_NAME="${1:-distribuidos-img}"
ROOT_DIR="${PWD}/${PROJECT_NAME}"

echo "Creando proyecto en: ${ROOT_DIR}"
mkdir -p "${ROOT_DIR}"

# -------------------------
# Directorios Backend
# -------------------------
mkdir -p "${ROOT_DIR}/backend/grpc_proto"
mkdir -p "${ROOT_DIR}/backend/__pycache__"
mkdir -p "${ROOT_DIR}/backend/tests"

# -------------------------
# Directorios Nodos
# -------------------------
mkdir -p "${ROOT_DIR}/nodes/worker"
mkdir -p "${ROOT_DIR}/nodes/grpc_proto"
mkdir -p "${ROOT_DIR}/nodes/__pycache__"

# -------------------------
# Directorios para data/logs
# -------------------------
mkdir -p "${ROOT_DIR}/data/input"
mkdir -p "${ROOT_DIR}/data/output"
mkdir -p "${ROOT_DIR}/logs"

# -------------------------
# .gitignore bÃƒÂ¡sico
# -------------------------
cat > "${ROOT_DIR}/.gitignore" << 'EOF'
__pycache__/
*.pyc
.env
.venv/
venv/
logs/
data/output/
EOF

# -------------------------
# requirements.txt
# -------------------------
cat > "${ROOT_DIR}/requirements.txt" << 'EOF'
fastapi
uvicorn
pydantic
pymysql
python-multipart
spyne
lxml
grpcio
grpcio-tools
EOF

# -------------------------
# README
# -------------------------
cat > "${ROOT_DIR}/README.md" << 'EOF'
### Sistema distribuido de procesamiento de imÃƒÂ¡genes (Avance 2)

Comandos rÃƒÂ¡pidos:
1) Crear venv e instalar:
    **Linux/macOS**
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

    **Windows (PowerShell)**
    ```powershell
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    ```

    Si PowerShell bloquea el script, ejecuta previamente `Set-ExecutionPolicy -Scope Process Bypass` en la misma ventana.

2) Generar stubs gRPC:
   python -m grpc_tools.protoc -I backend/grpc_proto --python_out=backend/grpc_proto --grpc_python_out=backend/grpc_proto backend/grpc_proto/image_worker.proto
   python -m grpc_tools.protoc -I nodes/grpc_proto --python_out=nodes/grpc_proto --grpc_python_out=nodes/grpc_proto nodes/grpc_proto/image_worker.proto

3) Levantar nodo:
   python nodes/worker/server.py

4) Levantar backend (Swagger en /docs):
   uvicorn backend.app:app --reload

5) Levantar SOAP (WSDL en http://127.0.0.1:9000/?wsdl):
   python backend/soap_service.py

Base de datos: ejecutar el script SQL provisto anteriormente para crear tablas.
EOF

# -------------------------
# gRPC .proto (duplicado en backend y nodes)
# -------------------------
PROTO_CONTENT='syntax = "proto3";
package imageworker;

service ImageWorker {
  rpc Health(HealthRequest) returns (HealthResponse);
  rpc SubmitJob(JobRequest) returns (JobAck);
}

message HealthRequest {}
message HealthResponse {
  string status = 1;
  string node_name = 2;
}

message Transformation {
  string code = 1;
  string params_json = 2;
  uint32 order = 3;
}

message ImageTask {
  string image_id = 1;
  string input_path = 2;
  string output_format = 3;
  repeated Transformation transforms = 4;
}

message JobRequest {
  string request_id = 1;
  repeated ImageTask images = 2;
}

message JobAck {
  string received = 1;
}
'
echo "$PROTO_CONTENT" > "${ROOT_DIR}/backend/grpc_proto/image_worker.proto"
echo "$PROTO_CONTENT" > "${ROOT_DIR}/nodes/grpc_proto/image_worker.proto"

# -------------------------
# backend: db.py
# -------------------------
cat > "${ROOT_DIR}/backend/db.py" << 'EOF'
import pymysql

def get_conn():
    return pymysql.connect(
        host="127.0.0.1",
        port=3306,
        user="tu_usuario",
        password="tu_password",
        database="distribuidos_img",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )
EOF

# -------------------------
# backend: models.py
# -------------------------
cat > "${ROOT_DIR}/backend/models.py" << 'EOF'
from .db import get_conn

def crear_solicitud(usuario_id:int, total:int)->int:
    sql = "INSERT INTO solicitudes (usuario_id, total_imagenes) VALUES (%s,%s)"
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (usuario_id, total))
        return cur.lastrowid

def registrar_imagen(solicitud_id:int, nombre:str, ruta:str, formato:str, formato_salida:str)->int:
    sql = """INSERT INTO imagenes (solicitud_id, nombre_original, ruta_entrada, formato_origen, formato_salida)
             VALUES (%s,%s,%s,%s,%s)"""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (solicitud_id, nombre, ruta, formato, formato_salida))
        return cur.lastrowid

def agregar_transformacion(imagen_id:int, codigo:str, orden:int, params_json:str|None):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM transformaciones WHERE codigo=%s", (codigo,))
        row = cur.fetchone()
        if not row:
            raise ValueError("TransformaciÃƒÂ³n no vÃƒÂ¡lida")
        cur.execute("""INSERT INTO imagen_transformaciones (imagen_id, transformacion_id, orden, parametros)
                       VALUES (%s,%s,%s,%s)""", (imagen_id, row["id"], orden, params_json))

def log(mensaje:str, nivel:str="INFO", componente:str="backend", nodo_id=None, solicitud_id=None, imagen_id=None):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""INSERT INTO logs (nivel, componente, nodo_id, solicitud_id, imagen_id, mensaje)
                       VALUES (%s,%s,%s,%s,%s,%s)""", (nivel, componente, nodo_id, solicitud_id, imagen_id, mensaje))
EOF

# -------------------------
# backend: grpc_client.py
# -------------------------
cat > "${ROOT_DIR}/backend/grpc_client.py" << 'EOF'
import grpc
from .grpc_proto import image_worker_pb2 as pb
from .grpc_proto import image_worker_pb2_grpc as pbg

def healthcheck(node_hostport:str):
    with grpc.insecure_channel(node_hostport) as channel:
        stub = pbg.ImageWorkerStub(channel)
        resp = stub.Health(pb.HealthRequest())
        return resp.status, resp.node_name

def submit_job(node_hostport:str, request_id:str, images:list[dict])->str:
    with grpc.insecure_channel(node_hostport) as channel:
        stub = pbg.ImageWorkerStub(channel)
        im_msgs = []
        for im in images:
            transforms = [pb.Transformation(code=t["code"], params_json=t.get("params_json","{}"), order=t.get("order",1))
                          for t in im.get("transforms",[])]
            im_msgs.append(pb.ImageTask(
                image_id=str(im["image_id"]),
                input_path=im["input_path"],
                output_format=im.get("output_format","jpg"),
                transforms=transforms
            ))
        ack = stub.SubmitJob(pb.JobRequest(request_id=request_id, images=im_msgs))
        return ack.received
EOF

# -------------------------
# backend: app.py (FastAPI Swagger)
# -------------------------
cat > "${ROOT_DIR}/backend/app.py" << 'EOF'
from fastapi import FastAPI
from pydantic import BaseModel
from .grpc_client import healthcheck, submit_job
from .models import log

app = FastAPI(title="Backend Interno - Imagenes", version="0.1")

class JobImage(BaseModel):
    image_id: int
    input_path: str
    output_format: str = "jpg"
    transforms: list[dict] = []

class SubmitBody(BaseModel):
    request_id: str
    node: str
    images: list[JobImage]

@app.get("/health/node")
def health(node: str):
    status, name = healthcheck(node)
    log(f"Healthcheck {node} -> {status}/{name}")
    return {"node": node, "status": status, "name": name}

@app.post("/jobs/submit")
def submit(body: SubmitBody):
    ack = submit_job(body.node, body.request_id, [im.dict() for im in body.images])
    log(f"Submit job {body.request_id} to {body.node}: {ack}")
    return {"ack": ack}
EOF

# -------------------------
# backend: soap_service.py
# -------------------------
cat > "${ROOT_DIR}/backend/soap_service.py" << 'EOF'
from wsgiref.simple_server import make_server
from spyne import Application, rpc, ServiceBase, Unicode, Array
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication

class ImageService(ServiceBase):
    @rpc(Unicode, _returns=Unicode)
    def ping(ctx, name):
        return f"pong {name}"

    @rpc(Unicode, Array(Unicode), _returns=Unicode)
    def crearSolicitud(ctx, usuario_id, imagenes):
        return f"Solicitud creada para usuario={usuario_id} con {len(imagenes)} imagen(es) [mock]"

    @rpc(Unicode, _returns=Unicode)
    def estadoSolicitud(ctx, solicitud_id):
        return f"Estado de {solicitud_id}: en_progreso (mock)"

    @rpc(Unicode, _returns=Unicode)
    def cancelarSolicitud(ctx, solicitud_id):
        return f"Solicitud {solicitud_id} cancelada (mock)"

soap_app = Application([ImageService], 'svc.imagenes',
                       in_protocol=Soap11(validator='lxml'),
                       out_protocol=Soap11())
wsgi_app = WsgiApplication(soap_app)

if __name__ == "__main__":
    server = make_server('0.0.0.0', 9000, wsgi_app)
    print("SOAP service on http://127.0.0.1:9000/?wsdl")
    server.serve_forever()
EOF

# -------------------------
# nodes: worker/processing.py
# -------------------------
cat > "${ROOT_DIR}/nodes/worker/processing.py" << 'EOF'
import time
def fake_process(image_task):
    time.sleep(0.2)
    return f"OK {image_task.image_id}"
EOF

# -------------------------
# nodes: worker/server.py
# -------------------------
cat > "${ROOT_DIR}/nodes/worker/server.py" << 'EOF'
import grpc
from concurrent import futures
from ..grpc_proto import image_worker_pb2 as pb
from ..grpc_proto import image_worker_pb2_grpc as pbg
from .processing import fake_process

NODE_NAME = "Nodo-Python-1"

class ImageWorkerServicer(pbg.ImageWorkerServicer):
    def Health(self, request, context):
        return pb.HealthResponse(status="OK", node_name=NODE_NAME)

    def SubmitJob(self, request, context):
        count = 0
        for im in request.images:
            fake_process(im)
            count += 1
        return pb.JobAck(received=f"OK: {count} images encoladas (mock)")

def serve(port=50051):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
    pbg.add_ImageWorkerServicer_to_server(ImageWorkerServicer(), server)
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"Node gRPC listening on {port} as {NODE_NAME}")
    server.wait_for_termination()

if __name__ == "__main__":
    serve(50051)
EOF

# -------------------------
# Mensaje final
# -------------------------
echo "Proyecto creado."
echo "Siguiente paso:"
echo "1) cd ${PROJECT_NAME}"
echo "2) py -m venv .venv"
echo "   - Linux/macOS: source .venv/bin/activate"
echo "   - Windows PowerShell: .\\.venv\\Scripts\\Activate.ps1"
echo "3) pip install -r requirements.txt"
echo "4) Genera los stubs gRPC (ver README)."
echo "5) Ejecuta: python nodes/worker/server.py y uvicorn backend.app:app --reload y python backend/soap_service.py"