# Ejemplos de Uso

Este directorio contiene ejemplos prácticos de cómo usar el sistema de procesamiento de imágenes.

## 📁 Archivos

### `batch_processing_example.py`
Ejemplo completo en Python que demuestra:
- Registro de usuario
- Login
- Procesamiento de múltiples imágenes con transformaciones específicas
- Descarga del archivo ZIP resultante

## 🚀 Cómo Ejecutar

### Prerrequisitos
1. Tener los servicios levantados:
   ```bash
   # Terminal 1
   python nodes/worker/server.py
   
   # Terminal 2
   python backend/soap_service.py
   
   # Terminal 3
   uvicorn backend.api:app --reload
   ```

2. Tener imágenes de prueba en `../img/`

### Ejecutar el Ejemplo

```bash
cd examples
python batch_processing_example.py
```

## 📝 Personalizar el Ejemplo

Puedes modificar las transformaciones en el archivo:

```python
# Ejemplo: Cambiar las transformaciones de la primera imagen
instructions = [
    {
        "filename": "imagen1.png",
        "output_format": "jpg",
        "transforms": [
            {"code": "GRAYSCALE", "order": 1},
            {"code": "BLUR", "params": {"radius": 5.0}, "order": 2},  # Cambiar aquí
            {"code": "WATERMARK", "params": {"text": "Mi Marca", "x": 10, "y": 10}, "order": 3}
        ]
    }
]
```

## 🎨 Transformaciones Disponibles

1. **GRAYSCALE** - Sin parámetros
2. **RESIZE** - `{"width": 800, "height": 600}`
3. **CROP** - `{"x": 100, "y": 100, "width": 500, "height": 500}`
4. **ROTATE** - `{"degrees": 90}`
5. **FLIP** - `{"axis": "horizontal"}` o `"vertical"`
6. **BLUR** - `{"radius": 2.0}`
7. **SHARPEN** - `{"factor": 1.5}`
8. **BRIGHTNESS_CONTRAST** - `{"brightness": 1.2, "contrast": 1.1}`
9. **WATERMARK** - `{"text": "Texto", "x": 10, "y": 10}`

## 📦 Resultado

El script genera un archivo `imagenes_procesadas.zip` con todas las imágenes transformadas.

## 🔧 Troubleshooting

### Error: "No module named 'requests'"
```bash
pip install requests
```

### Error: "No se pudo resolver la ruta del archivo"
Verifica que las rutas en `IMAGE_PATHS` sean correctas.

### Error: "Connection refused"
Verifica que los tres servicios estén corriendo.

## 📚 Más Ejemplos

Ver también:
- `../scripts/test_batch_processing.ps1` - Versión PowerShell
- `../HTTP_EXAMPLES.md` - Ejemplos con cURL y otras herramientas
- `../DOCUMENTATION.md` - Documentación completa
