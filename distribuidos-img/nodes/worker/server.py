"""
Servidor gRPC del Nodo Worker
===============================
Este es el componente que realmente procesa las imágenes de forma distribuida.

Funcionalidades:
- Recibe lotes de imágenes del backend vía gRPC
- Aplica transformaciones (resize, crop, filters, etc.)
- Devuelve resultados con rutas de archivos procesados
- Responde a healthchecks para monitoreo

Cada nodo worker es un servidor independiente que puede ejecutarse en 
diferentes máquinas para escalar horizontalmente el procesamiento.
"""

from __future__ import annotations

from concurrent import futures
import logging
import os
import sys

import grpc

# Configuración de rutas para permitir ejecución como paquete o script
# Esto permite ejecutar: python -m nodes.worker.server  O  python nodes/worker/server.py
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Importa los protobuf generados para gRPC
from nodes.grpc_proto import image_worker_pb2 as pb
from nodes.grpc_proto import image_worker_pb2_grpc as pbg
# Importa la lógica de procesamiento de imágenes
from nodes.worker.processing import process_image_task

# Configuración del sistema de logging
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")

# Nombre identificador de este nodo (puede cambiarse para cada instancia)
NODE_NAME = "Nodo-Python-1"


class ImageWorkerServicer(pbg.ImageWorkerServicer):
    """
    Implementación del servicio gRPC ImageWorker.
    
    Esta clase define los métodos RPC que el backend puede llamar:
    - Health: Para verificar disponibilidad del nodo
    - SubmitJob: Para enviar trabajos de procesamiento
    """

    def Health(self, request, context):  # noqa: N802 (nombre gRPC)
        """
        Método RPC para healthcheck.
        
        Args:
            request: HealthRequest (protobuf vacío)
            context: Contexto de la llamada gRPC
            
        Returns:
            HealthResponse con estado "OK" y nombre del nodo
        """
        return pb.HealthResponse(status="OK", node_name=NODE_NAME)

    def SubmitJob(self, request, context):  # noqa: N802
        """
        Método RPC principal: recibe y procesa un lote de imágenes.
        
        Args:
            request: JobRequest con request_id y lista de ImageTask
            context: Contexto de la llamada gRPC
            
        Returns:
            JobAck con resultados del procesamiento de cada imagen
            
        Proceso:
        1. Itera sobre cada imagen en el request
        2. Procesa cada imagen aplicando sus transformaciones
        3. Recolecta resultados (éxito o error)
        4. Retorna resumen del trabajo
        """
        results = []
        overall_ok = True  # Bandera para saber si todo salió bien

        # Procesa cada imagen del lote
        for image_task in request.images:
            # Llama a la función de procesamiento (en processing.py)
            status, output_path, error = process_image_task(image_task, request.request_id)
            
            # Si alguna falla, marca overall_ok como False
            if status != "ok":
                overall_ok = False
            
            # Agrega el resultado de esta imagen
            results.append(pb.ImageResult(
                image_id=image_task.image_id,
                output_path=output_path or "",
                status=status,
                error=error or "",
            ))

        # Genera mensaje resumen
        ok_count = sum(1 for r in results if r.status == "ok")
        message = f"Procesadas {ok_count}/{len(results)} imágenes"
        logging.info("[WORKER] %s", message)
        
        # Retorna el resultado completo al backend
        return pb.JobAck(ok=overall_ok, message=message, results=results)


def serve(port: int = 50051):
    """
    Inicia el servidor gRPC del nodo worker.
    
    Args:
        port: Puerto donde escuchará el servidor (default: 50051)
        
    El servidor:
    - Utiliza un ThreadPoolExecutor con 8 workers para procesar múltiples
      requests concurrentemente
    - Escucha en todas las interfaces de red (::)
    - Se ejecuta de forma bloqueante hasta ser terminado (Ctrl+C)
    """
    # Crea el servidor gRPC con pool de 8 threads para concurrencia
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
    
    # Registra nuestra implementación del servicio
    pbg.add_ImageWorkerServicer_to_server(ImageWorkerServicer(), server)
    
    # Escucha en el puerto especificado (IPv4 e IPv6)
    server.add_insecure_port(f"[::]:{port}")
    
    logging.info("[WORKER] gRPC escuchando en %s como %s", port, NODE_NAME)
    
    # Inicia el servidor
    server.start()
    
    # Bloquea hasta que se termine el servidor (Ctrl+C)
    server.wait_for_termination()


# Punto de entrada cuando se ejecuta como script
if __name__ == "__main__":
    serve()