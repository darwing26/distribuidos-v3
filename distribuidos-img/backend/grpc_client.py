"""
Cliente gRPC para comunicación con los nodos workers.
Este módulo facilita la comunicación entre el backend y los nodos de procesamiento
mediante el protocolo gRPC (Remote Procedure Call de Google).
"""

import grpc

from nodes.grpc_proto import image_worker_pb2 as pb  # type: ignore
from nodes.grpc_proto import image_worker_pb2_grpc as pbg  # type: ignore

def healthcheck(node_hostport:str):
    """
    Verifica el estado de salud de un nodo worker.
    
    Args:
        node_hostport: Dirección del nodo en formato "host:puerto" (ej: "127.0.0.1:50051")
    
    Returns:
        tuple: (status, node_name) - Estado del nodo y su nombre identificador
    """
    # Crea un canal de comunicación inseguro (sin TLS/SSL) con el nodo
    with grpc.insecure_channel(node_hostport) as channel:
        # Crea un stub (cliente) para llamar a los métodos del servicio ImageWorker
        stub = pbg.ImageWorkerStub(channel)
        # Llama al método Health del nodo y obtiene la respuesta
        resp = stub.Health(pb.HealthRequest())
        return resp.status, resp.node_name

def submit_job(node_hostport:str, request_id:str, images:list[dict])->dict:
    """
    Envía un trabajo de procesamiento de imágenes a un nodo worker mediante gRPC.
    
    Este método es el núcleo de la comunicación distribuida: envía un lote de imágenes
    con sus transformaciones al nodo worker para que las procese.
    
    Args:
        node_hostport: Dirección del nodo worker (ej: "127.0.0.1:50051")
        request_id: Identificador único de la solicitud para tracking
        images: Lista de diccionarios, cada uno con:
            - image_id: ID de la imagen en la BD
            - input_path: Ruta del archivo de entrada
            - output_format: Formato de salida deseado (jpg, png, tif)
            - transforms: Lista de transformaciones a aplicar

    Returns:
        dict: Resultado del trabajo con la estructura:
            {
                "ok": bool,           # Si el trabajo se completó exitosamente
                "message": str,       # Mensaje descriptivo del resultado
                "results": [          # Lista de resultados por cada imagen
                    {
                        "image_id": str,
                        "output_path": str,
                        "status": str,
                        "error": str
                    }
                ]
            }
    """
    # Establece conexión gRPC con el nodo
    with grpc.insecure_channel(node_hostport) as channel:
        stub = pbg.ImageWorkerStub(channel)
        
        # Convierte cada imagen del diccionario Python a mensaje protobuf
        im_msgs = []
        for im in images:
            # Convierte las transformaciones a mensajes protobuf
            transforms = [pb.Transformation(code=t["code"], params_json=t.get("params_json","{}"), order=t.get("order",1))
                          for t in im.get("transforms",[])]
            
            # Crea el mensaje ImageTask con toda la información de la imagen
            im_msgs.append(pb.ImageTask(
                image_id=str(im["image_id"]),
                input_path=im["input_path"],
                output_format=im.get("output_format","jpg"),
                transforms=transforms
            ))
        
        # Envía el trabajo al nodo y espera la respuesta
        ack = stub.SubmitJob(pb.JobRequest(request_id=request_id, images=im_msgs))
        
        # Convierte la respuesta protobuf a un diccionario Python
        return {
            "ok": ack.ok,
            "message": ack.message,
            "results": [
                {
                    "image_id": res.image_id,
                    "output_path": res.output_path,
                    "status": res.status,
                    "error": res.error,
                }
                for res in ack.results
            ],
        }
