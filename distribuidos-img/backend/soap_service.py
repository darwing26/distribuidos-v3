"""Servidor SOAP que actúa como capa de aplicación/orquestador."""

from __future__ import annotations

import json
import os
import sys
from wsgiref.simple_server import make_server

from spyne import Application, rpc, ServiceBase, Unicode, Array
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication

# Permite correr como script (python backend/soap_service.py)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.grpc_client import submit_job
from backend.models import (
    crear_solicitud,
    registrar_imagen,
    agregar_transformacion,
    actualizar_estado_imagen,
    actualizar_estado_solicitud,
    obtener_estado_solicitud,
    obtener_nodos_activos,
    log,
)


DEFAULT_NODE = "127.0.0.1:50051"
NAMESPACE = "svc.imagenes"


def _parse_imagen_payload(raw: str) -> dict:
    """Convierte la entrada string (JSON) a un diccionario validado."""

    data = json.loads(raw)
    if not isinstance(data, dict):  # pragma: no cover
        raise ValueError("La imagen enviada debe ser un objeto JSON")
    return data


class ImageService(ServiceBase):
    @rpc(Unicode, _returns=Unicode)
    def ping(ctx, nombre):  # noqa: N802
        return f"pong {nombre}"

    @rpc(Unicode, Array(Unicode), _returns=Unicode)
    def crearSolicitud(ctx, usuario_id, imagenes):  # noqa: N802
        uid = int(usuario_id)
        imagenes = list(imagenes or [])

        solicitud_id = crear_solicitud(uid, len(imagenes))
        log(f"Solicitud {solicitud_id} creada", componente="soap", solicitud_id=solicitud_id)

        trabajo = []
        for idx, raw in enumerate(imagenes, start=1):
            payload = _parse_imagen_payload(raw)
            input_path = payload.get("input_path")
            if not input_path:
                raise ValueError(f"Imagen #{idx} sin input_path")

            nombre = payload.get("original_name") or os.path.basename(input_path)
            formato_in = payload.get("input_format") or os.path.splitext(input_path)[1].lstrip(".") or "jpg"
            formato_out = payload.get("output_format", "jpg")

            imagen_id = registrar_imagen(solicitud_id, nombre, input_path, formato_in, formato_out)

            transforms = payload.get("transforms", []) or []
            normalizados = []
            for orden, tr in enumerate(transforms, start=1):
                codigo = str(tr.get("code", "")).upper()
                params = tr.get("params", {})
                params_json = json.dumps(params) if isinstance(params, dict) else str(params)
                agregar_transformacion(imagen_id, codigo, tr.get("order", orden), params_json)
                normalizados.append({
                    "code": codigo,
                    "order": tr.get("order", orden),
                    "params_json": params_json,
                })

            if not normalizados:
                normalizados.append({"code": "GRAYSCALE", "order": 1, "params_json": "{}"})

            trabajo.append({
                "image_id": imagen_id,
                "input_path": input_path,
                "output_format": formato_out,
                "transforms": normalizados,
            })

        nodos = obtener_nodos_activos()
        destino = nodos[0]["direccion"] if nodos else DEFAULT_NODE
        log(f"Enviando solicitud {solicitud_id} al nodo {destino}", componente="soap", solicitud_id=solicitud_id)

        ack = submit_job(destino, str(solicitud_id), trabajo)

        for res in ack["results"]:
            actualizar_estado_imagen(
                int(res["image_id"]),
                res.get("status"),
                ruta_salida=res.get("output_path"),
                mensaje_error=res.get("error"),
            )

        actualizar_estado_solicitud(solicitud_id, "completada" if ack["ok"] else "fallida")
        log(f"Solicitud {solicitud_id} finalizada: {ack['message']}", componente="soap", solicitud_id=solicitud_id)

        return json.dumps({
            "solicitud_id": solicitud_id,
            "ok": ack["ok"],
            "message": ack["message"],
            "results": ack["results"],
        })

    @rpc(Unicode, _returns=Unicode)
    def estadoSolicitud(ctx, solicitud_id):  # noqa: N802
        solicitud_id = int(solicitud_id)
        sol, imgs = obtener_estado_solicitud(solicitud_id)
        if not sol:
            return json.dumps({"error": "Solicitud no encontrada"})
        return json.dumps({"solicitud": sol, "imagenes": imgs})

    @rpc(Unicode, _returns=Unicode)
    def cancelarSolicitud(ctx, solicitud_id):  # noqa: N802
        solicitud_id = int(solicitud_id)
        actualizar_estado_solicitud(solicitud_id, "cancelada")
        log(f"Solicitud {solicitud_id} cancelada", componente="soap", solicitud_id=solicitud_id)
        return json.dumps({"solicitud_id": solicitud_id, "status": "cancelada"})


soap_app = Application([ImageService], NAMESPACE, in_protocol=Soap11(validator='lxml'), out_protocol=Soap11())
wsgi_app = WsgiApplication(soap_app)


def main(host: str = "0.0.0.0", port: int = 9000):
    print(f"SOAP service on http://{host}:{port}/?wsdl")
    server = make_server(host, port, wsgi_app)
    server.serve_forever()


if __name__ == "__main__":
    main()