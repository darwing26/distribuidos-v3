"""
Orquestador de Procesamiento Distribuido
=========================================
Este módulo coordina la distribución de trabajos de procesamiento de imágenes
entre múltiples nodos workers usando un algoritmo de round-robin.

Responsabilidades:
- Obtener nodos workers activos de la BD
- Consultar trabajos pendientes de una solicitud
- Distribuir trabajos entre nodos disponibles
- Actualizar estados de procesamiento en la BD
"""

# backend/orchestrator.py
from backend.db import get_conn
from backend.grpc_client import submit_job
from backend.models import log, actualizar_estado_imagen

def obtener_nodos_activos():
    """
    Consulta la base de datos para obtener todos los nodos workers activos.
    
    Returns:
        list: Lista de nodos con formato [{"id": int, "direccion": str}, ...]
              donde dirección es "host:puerto" (ej: "127.0.0.1:50051")
    """
    conn = get_conn()
    cur = conn.cursor()
    
    # Busca nodos que usan gRPC y están en estado activo
    cur.execute("SELECT id, direccion FROM nodos WHERE protocolo='grpc' AND estado='activo'")
    rows = cur.fetchall()
    
    cur.close()
    conn.close()
    return rows

def obtener_trabajos(solicitud_id):
    """
    Obtiene todas las imágenes pendientes de procesamiento para una solicitud específica.
    
    Para cada imagen, recupera sus transformaciones asociadas ordenadas por secuencia.
    
    Args:
        solicitud_id: ID de la solicitud en la base de datos
    
    Returns:
        list: Lista de trabajos, cada uno con formato:
            {
                "imagen_id": int,
                "input_path": str,
                "output_format": str,
                "transforms": [
                    {
                        "code": str,       # Ej: "RESIZE", "GRAYSCALE"
                        "order": int,      # Orden de aplicación
                        "params_json": str # Parámetros en JSON
                    }
                ]
            }
    """
    conn = get_conn()
    cur = conn.cursor()
    
    # Obtiene todas las imágenes pendientes de esta solicitud
    cur.execute("""
        SELECT i.id, i.ruta_entrada, i.formato_salida
        FROM imagenes i
        WHERE i.solicitud_id=%s AND i.estado='pendiente'
    """, (solicitud_id,))
    imgs = cur.fetchall()

    jobs = []
    # Para cada imagen, construye su trabajo con todas sus transformaciones
    for item in imgs:
        # Maneja tanto formato dict como tupla (compatibilidad)
        img_id = item["id"] if isinstance(item, dict) else item[0]
        input_path = item["ruta_entrada"] if isinstance(item, dict) else item[1]
        fmt_out = item["formato_salida"] if isinstance(item, dict) else item[2]
        
        # Obtiene las transformaciones de esta imagen ordenadas por secuencia
        cur.execute("""
            SELECT codigo, orden, params_json
            FROM imagen_transformaciones
            WHERE imagen_id=%s ORDER BY orden ASC
        """, (img_id,))
        
        # Construye la lista de transformaciones
        transforms = [
            {
                "code": row["codigo"],
                "order": row["orden"],
                "params_json": row.get("params_json", "{}"),
            }
            for row in cur.fetchall()
        ]
        
        # Agrega el trabajo completo a la lista
        jobs.append({
            "imagen_id": img_id,
            "input_path": input_path,
            "output_format": fmt_out,
            "transforms": transforms,
        })
    
    cur.close()
    conn.close()
    return jobs

def orquestar_solicitud(solicitud_id: int):
    """
    Función principal de orquestación: distribuye los trabajos de una solicitud
    entre los nodos workers disponibles usando round-robin.
    
    Este es el algoritmo de balanceo de carga: distribuye equitativamente
    las imágenes entre todos los nodos activos.
    
    Args:
        solicitud_id: ID de la solicitud a procesar
    
    Raises:
        RuntimeError: Si no hay nodos activos disponibles
        
    Proceso:
    1. Obtiene lista de nodos activos
    2. Obtiene lista de trabajos pendientes
    3. Distribuye trabajos usando round-robin (1 imagen por nodo, rotando)
    4. Actualiza estados en la BD según resultados
    """
    # Paso 1: Verifica que haya nodos disponibles
    nodos = obtener_nodos_activos()
    if not nodos:
        raise RuntimeError("No hay nodos gRPC activos")

    # Paso 2: Obtiene los trabajos pendientes
    trabajos = obtener_trabajos(solicitud_id)
    if not trabajos:
        log("No hay trabajos para orquestar", componente="orq", solicitud_id=solicitud_id)
        return

    # Paso 3: Distribución Round-Robin
    # idx mantiene el índice del nodo actual en la rotación
    idx = 0
    for job in trabajos:
        # Selecciona el siguiente nodo (usa módulo para ciclar)
        nodo = nodos[idx % len(nodos)]
        idx += 1
        
        # Extrae información del nodo (compatible con dict y tupla)
        if isinstance(nodo, dict):
            nodo_id = nodo.get("id")
            direccion = nodo.get("direccion")
        else:
            nodo_id, direccion = nodo
        
        try:
            # Marca la imagen como "en progreso"
            actualizar_estado_imagen(job["imagen_id"], "en_progreso", nodo_id=nodo_id)
            
            # Envía el trabajo al nodo worker vía gRPC
            # IMPORTANTE: Usar solo solicitud_id como request_id para que todas las imágenes
            # de la misma solicitud se guarden en la misma carpeta
            ack = submit_job(
                direccion,
                str(solicitud_id),  # Todas las imágenes de esta solicitud van a la misma carpeta
                [
                    {
                        "image_id": job["imagen_id"],
                        "input_path": job["input_path"],
                        "output_format": job["output_format"],
                        "transforms": job["transforms"],
                    }
                ],
            )
            
            # Procesa el resultado del nodo
            resultado = ack["results"][0] if ack.get("results") else {
                "status": "error",
                "error": "Sin resultado"
            }
            
            # Actualiza el estado según el resultado
            if resultado["status"] == "ok":
                # Procesamiento exitoso
                actualizar_estado_imagen(job["imagen_id"], "procesada", 
                                       ruta_salida=resultado.get("output_path"), 
                                       nodo_id=nodo_id)
            else:
                # Error en el procesamiento
                actualizar_estado_imagen(job["imagen_id"], "error", 
                                       nodo_id=nodo_id, 
                                       mensaje_error=resultado.get("error"))
                log(f"Error job imagen={job['imagen_id']}: {resultado.get('error')}", 
                    nivel="ERROR", componente="orq", solicitud_id=solicitud_id)
                    
        except Exception as e:
            # Manejo de excepciones: errores de red, timeouts, etc.
            actualizar_estado_imagen(job["imagen_id"], "error", nodo_id=nodo_id)
            log(f"Excepción al enviar job: {e}", 
                nivel="ERROR", componente="orq", solicitud_id=solicitud_id)