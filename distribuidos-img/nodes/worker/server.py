"""Servidor gRPC del nodo worker.

Recibe lotes de imágenes, aplica transformaciones declaradas y devuelve un
listado de resultados con las rutas de salida generadas.
"""

from __future__ import annotations

from concurrent import futures
import logging
import os
import sys

import grpc

# Permite ejecutar este módulo tanto como paquete (python -m nodes.worker.server)
# como script directo (python nodes/worker/server.py)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from nodes.grpc_proto import image_worker_pb2 as pb
from nodes.grpc_proto import image_worker_pb2_grpc as pbg
from nodes.worker.processing import process_image_task

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")


NODE_NAME = "Nodo-Python-1"


class ImageWorkerServicer(pbg.ImageWorkerServicer):
    """Implementación del servicio ImageWorker."""

    def Health(self, request, context):  # noqa: N802 (nombre gRPC)
        return pb.HealthResponse(status="OK", node_name=NODE_NAME)

    def SubmitJob(self, request, context):  # noqa: N802
        results = []
        overall_ok = True

        for image_task in request.images:
            status, output_path, error = process_image_task(image_task, request.request_id)
            if status != "ok":
                overall_ok = False
            results.append(pb.ImageResult(
                image_id=image_task.image_id,
                output_path=output_path or "",
                status=status,
                error=error or "",
            ))

        ok_count = sum(1 for r in results if r.status == "ok")
        message = f"Procesadas {ok_count}/{len(results)} imágenes"
        logging.info("[WORKER] %s", message)
        return pb.JobAck(ok=overall_ok, message=message, results=results)


def serve(port: int = 50051):
    """Arranca el servidor gRPC."""

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
    pbg.add_ImageWorkerServicer_to_server(ImageWorkerServicer(), server)
    server.add_insecure_port(f"[::]:{port}")
    logging.info("[WORKER] gRPC escuchando en %s como %s", port, NODE_NAME)
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()