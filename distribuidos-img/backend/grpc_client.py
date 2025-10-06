import grpc

from nodes.grpc_proto import image_worker_pb2 as pb  # type: ignore
from nodes.grpc_proto import image_worker_pb2_grpc as pbg  # type: ignore

def healthcheck(node_hostport:str):
    with grpc.insecure_channel(node_hostport) as channel:
        stub = pbg.ImageWorkerStub(channel)
        resp = stub.Health(pb.HealthRequest())
        return resp.status, resp.node_name

def submit_job(node_hostport:str, request_id:str, images:list[dict])->dict:
    """Envía un JobRequest y devuelve un diccionario con resultados.

    Retorna estructura: {"ok": bool, "message": str, "results": [...]}
    """

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
