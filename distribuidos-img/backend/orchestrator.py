# backend/orchestrator.py
from backend.db import get_conn
from backend.grpc_client import submit_job
from backend.models import log, actualizar_estado_imagen

def obtener_nodos_activos():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT id, direccion FROM nodos WHERE protocolo='grpc' AND estado='activo'")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def obtener_trabajos(solicitud_id):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT i.id, i.ruta_entrada, i.formato_salida
        FROM imagenes i
        WHERE i.solicitud_id=%s AND i.estado='pendiente'
    """, (solicitud_id,))
    imgs = cur.fetchall()

    jobs = []
    for item in imgs:
        img_id = item["id"] if isinstance(item, dict) else item[0]
        input_path = item["ruta_entrada"] if isinstance(item, dict) else item[1]
        fmt_out = item["formato_salida"] if isinstance(item, dict) else item[2]
        cur.execute("""
            SELECT codigo, orden, params_json
            FROM imagen_transformaciones
            WHERE imagen_id=%s ORDER BY orden ASC
        """, (img_id,))
        transforms = [
            {
                "code": row["codigo"],
                "order": row["orden"],
                "params_json": row.get("params_json", "{}"),
            }
            for row in cur.fetchall()
        ]
        jobs.append({
            "imagen_id": img_id,
            "input_path": input_path,
            "output_format": fmt_out,
            "transforms": transforms,
        })
    cur.close(); conn.close()
    return jobs

def orquestar_solicitud(solicitud_id: int):
    nodos = obtener_nodos_activos()
    if not nodos:
        raise RuntimeError("No hay nodos gRPC activos")

    trabajos = obtener_trabajos(solicitud_id)
    if not trabajos:
        log("No hay trabajos para orquestar", componente="orq", solicitud_id=solicitud_id)
        return

    # Round-robin simple
    idx = 0
    for job in trabajos:
        nodo = nodos[idx % len(nodos)]
        idx += 1
        if isinstance(nodo, dict):
            nodo_id = nodo.get("id")
            direccion = nodo.get("direccion")
        else:
            nodo_id, direccion = nodo
        try:
            actualizar_estado_imagen(job["imagen_id"], "en_progreso", nodo_id=nodo_id)
            ack = submit_job(
                direccion,
                f"{solicitud_id}-{job['imagen_id']}",
                [
                    {
                        "image_id": job["imagen_id"],
                        "input_path": job["input_path"],
                        "output_format": job["output_format"],
                        "transforms": job["transforms"],
                    }
                ],
            )
            resultado = ack["results"][0] if ack.get("results") else {
                "status": "error",
                "error": "Sin resultado"
            }
            if resultado["status"] == "ok":
                actualizar_estado_imagen(job["imagen_id"], "procesada", ruta_salida=resultado.get("output_path"), nodo_id=nodo_id)
            else:
                actualizar_estado_imagen(job["imagen_id"], "error", nodo_id=nodo_id, mensaje_error=resultado.get("error"))
                log(f"Error job imagen={job['imagen_id']}: {resultado.get('error')}", nivel="ERROR", componente="orq", solicitud_id=solicitud_id)
        except Exception as e:
            actualizar_estado_imagen(job["imagen_id"], "error", nodo_id=nodo_id)
            log(f"Excepción al enviar job: {e}", nivel="ERROR", componente="orq", solicitud_id=solicitud_id)