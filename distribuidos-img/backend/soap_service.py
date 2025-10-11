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

from backend.orchestrator import orquestar_solicitud
from backend.models import (
    crear_solicitud,
    registrar_imagen,
    agregar_transformacion,
    actualizar_estado_solicitud,
    obtener_estado_solicitud,
    log,
)

# Namespace SOAP para el servicio
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
        """
        Método SOAP principal para crear y procesar una solicitud de procesamiento de imágenes.
        
        Este método:
        1. Crea una solicitud en la BD
        2. Registra cada imagen con sus transformaciones
        3. Delega al orquestador que distribuye los trabajos entre nodos usando round-robin
        4. El orquestador envía los trabajos vía gRPC a los workers
        5. Retorna el resultado de la operación
        
        Args:
            usuario_id: ID del usuario que hace la solicitud
            imagenes: Array de strings JSON, cada uno con:
                - input_path: Ruta del archivo
                - original_name: Nombre original
                - input_format: Formato de entrada (jpg, png, etc.)
                - output_format: Formato de salida deseado
                - transforms: Lista de transformaciones a aplicar
        
        Returns:
            String JSON con el resultado: {solicitud_id, ok, message}
        """
        uid = int(usuario_id)
        imagenes = list(imagenes or [])

        # Paso 1: Crear la solicitud en la base de datos
        solicitud_id = crear_solicitud(uid, len(imagenes))
        log(f"Solicitud {solicitud_id} creada", componente="soap", solicitud_id=solicitud_id)

        # Paso 2: Procesar cada imagen y registrarla en la BD
        for idx, raw in enumerate(imagenes, start=1):
            payload = _parse_imagen_payload(raw)
            input_path = payload.get("input_path")
            if not input_path:
                raise ValueError(f"Imagen #{idx} sin input_path")

            # Extrae información de la imagen
            nombre = payload.get("original_name") or os.path.basename(input_path)
            formato_in = payload.get("input_format") or os.path.splitext(input_path)[1].lstrip(".") or "jpg"
            formato_out = payload.get("output_format", "jpg")

            # Registra la imagen en la BD con estado 'pendiente'
            imagen_id = registrar_imagen(solicitud_id, nombre, input_path, formato_in, formato_out)

            # Procesa y registra las transformaciones en la BD
            transforms = payload.get("transforms", []) or []
            for orden, tr in enumerate(transforms, start=1):
                codigo = str(tr.get("code", "")).upper()
                params = tr.get("params", {})
                
                # Normaliza parámetros a formato JSON string
                if isinstance(params, dict):
                    params_json = json.dumps(params)
                elif isinstance(params, str):
                    # Si ya es string, verificar que sea JSON válido
                    try:
                        json.loads(params)
                        params_json = params
                    except json.JSONDecodeError:
                        params_json = "{}"
                else:
                    params_json = "{}"
                
                # Registra la transformación en la tabla imagen_transformaciones
                agregar_transformacion(imagen_id, codigo, tr.get("order", orden), params_json)

        # Ahora el orquestador se encarga de distribuir los trabajos entre los nodos
        # usando round-robin y actualizar los estados en la BD
        log(f"Iniciando orquestación de solicitud {solicitud_id}", componente="soap", solicitud_id=solicitud_id)
        
        try:
            # El orquestador distribuye las imágenes entre los nodos activos vía gRPC
            orquestar_solicitud(solicitud_id)
            
            # Marca la solicitud como completada
            actualizar_estado_solicitud(solicitud_id, "completada")
            log(f"Solicitud {solicitud_id} completada exitosamente", componente="soap", solicitud_id=solicitud_id)
            
            return json.dumps({
                "solicitud_id": solicitud_id,
                "ok": True,
                "message": f"Solicitud {solicitud_id} procesada correctamente",
            })
            
        except Exception as e:
            # Si hay error, marca la solicitud como fallida
            actualizar_estado_solicitud(solicitud_id, "fallida")
            log(f"Error en solicitud {solicitud_id}: {str(e)}", nivel="ERROR", componente="soap", solicitud_id=solicitud_id)
            
            return json.dumps({
                "solicitud_id": solicitud_id,
                "ok": False,
                "message": f"Error al procesar solicitud: {str(e)}",
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