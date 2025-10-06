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

3) Levantar nodo trabajador gRPC:
   python nodes/worker/server.py

4) Levantar servidor SOAP (WSDL en http://127.0.0.1:9000/?wsdl):
   python backend/soap_service.py

5) Levantar API cliente (recibe uploads y llama SOAP):
   uvicorn backend.api:app --reload

Base de datos: ejecutar el script SQL provisto anteriormente para crear tablas.

### Flujo end-to-end (Avance 2)

1. El cliente HTTP (`backend/api.py`) recibe un `multipart/form-data` con la imagen y los parámetros del pipeline.
2. El cliente construye un payload JSON y lo envía al servidor de aplicación vía SOAP (`backend/soap_service.py`).
3. El servidor SOAP registra la solicitud en MySQL, selecciona un nodo gRPC y delega el trabajo usando `SubmitJob`.
4. El nodo worker (`nodes/worker/server.py`) procesa las transformaciones (grayscale, resize, crop, blur, etc.) con Pillow y guarda la imagen resultante en `data/output/<solicitud>/`.
5. El servidor SOAP actualiza estado en base de datos y responde con un JSON de resumen (incluido dentro de la respuesta SOAP).

### Endpoints adicionales (Avance 3)

- **POST `/signup`** – Registra un usuario nuevo. Cuerpo JSON:

   ```json
   {
      "username": "usuario_demo",
      "email": "demo@example.com",
      "password": "secreto123"
   }
   ```

   Respuesta: `{ "usuario_id": 1, "username": "usuario_demo", ... }`

- **POST `/login`** – Inicia sesión validando credenciales. Cuerpo JSON:

   ```json
   {
      "username": "usuario_demo",
      "password": "secreto123"
   }
   ```

   Respuesta: `{ "usuario_id": 1, "username": "usuario_demo", "estado": "activo" }`

Utiliza el `usuario_id` devuelto por `/login` al invocar `/procesar-imagen`.

### Ejemplo de solicitud desde cliente (PowerShell)

```powershell
$body = @{
    usuario_id = "1"
    output_format = "png"
    transforms = '[{"code":"grayscale"},{"code":"resize","params":{"width":256,"height":256}}]'
    file = Get-Item "path\a\tu_imagen.jpg"
}
Invoke-RestMethod -Uri http://127.0.0.1:8000/procesar-imagen -Method Post -Form $body
```

El campo `transforms` acepta una lista JSON con las transformaciones a aplicar en orden. Si se omite, se aplica conversión a escala de grises por defecto.
