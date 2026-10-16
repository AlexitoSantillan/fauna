# Fauna Amenazada Huánuco · INNOBEST 2026

App web (Python + Flask) que identifica con IA mamíferos amenazados de Huánuco
(oso de anteojos, mono choro de cola amarilla, mono araña de cara negra) y guarda los
avistamientos en MongoDB.

- **Identificar:** subes una foto y el modelo (YOLO11n-cls exportado a ONNX) da las probabilidades.
- **Guardar:** corriges la especie si hace falta, eliges la provincia y se guarda en MongoDB.
- **Registros:** panel con conteos por especie y tarjetas con cada avistamiento.
- **API:** `/api/avistamientos`, `/api/estadisticas`, `/salud`.

## Estructura

```
app.py              rutas de Flask
modelo.py           inferencia con ONNX Runtime
db.py               MongoDB (con respaldo en memoria si no hay conexión)
especies.py         fichas de especies, provincias, líneas del INNOBEST
templates/ static/  páginas y estilos
model/best.onnx     <- el modelo (lo generas en el paso 1)
convertir_modelo.py convierte best.pt a best.onnx (se usa en Colab)
render.yaml         configuración de Render
```

## Paso 1 · Convertir el modelo (Colab, 3 minutos)

En la terminal de Colab, con `best.pt` y la carpeta `dataset/` en `/content`:

```
pip install -q ultralytics onnx onnxruntime
python convertir_modelo.py best.pt dataset/val
```

Al final debe decir que `best.pt` y `best.onnx` coinciden en casi todas las fotos.
Descarga `best.onnx` y cópialo a la carpeta `model/` de este proyecto.

## Paso 2 · Probar en tu computadora (opcional)

```
pip install -r requirements.txt
python app.py
```
Abre http://localhost:5000. Sin MongoDB funciona en “modo local”.

## Paso 3 · MongoDB Atlas (gratis)

1. Entra a https://www.mongodb.com/atlas y crea una cuenta.
2. Crea un clúster gratuito (M0).
3. **Database Access** → Add New Database User → usuario y contraseña (usa una contraseña
   sin símbolos raros, o tendrás que codificarlos en la URL).
4. **Network Access** → Add IP Address → **Allow access from anywhere** (`0.0.0.0/0`).
   Render usa IPs que cambian, por eso es necesario.
5. **Database** → Connect → Drivers → copia la cadena de conexión. Se ve así:
   `mongodb+srv://USUARIO:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority`
   Reemplaza `<password>` por tu contraseña real.

## Paso 4 · Subir el proyecto a GitHub

1. Crea un repositorio en https://github.com/new (puede ser privado).
2. Sube **todo el contenido de esta carpeta**, incluido `model/best.onnx`
   (“Add file → Upload files” arrastrando los archivos y carpetas).

## Paso 5 · Desplegar en Render

1. Entra a https://render.com y crea una cuenta con GitHub.
2. **New → Web Service** → elige tu repositorio.
3. Configura:
   - Runtime: **Python 3**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app --workers 1 --threads 4 --timeout 120`
   - Plan: **Free**
4. En **Environment** agrega:
   - `MONGODB_URI` = tu cadena de conexión de Atlas
   - `PYTHON_VERSION` = `3.12.8`
5. **Create Web Service**. El primer despliegue tarda unos minutos.
6. Abre `https://TU-APP.onrender.com/salud`. Debe decir
   `"modelo":"ok"` y `"base_de_datos":"mongodb"`.

## Si algo falla

| Síntoma | Causa probable |
|---|---|
| `/salud` dice `modelo: error ... FileNotFoundError` | Falta `model/best.onnx` en el repositorio |
| `/salud` dice `base_de_datos: memoria` | `MONGODB_URI` mal escrita, contraseña con símbolos, o falta `0.0.0.0/0` en Network Access. `error_base_de_datos` da una pista |
| La página tarda ~1 minuto en abrir | Render gratis se “duerme” tras 15 min sin visitas. Ábrela 2 minutos antes de exponer |
| Error al instalar en Render | Revisa que `PYTHON_VERSION` sea `3.12.8` |

## Límites

- El modelo solo conoce 3 especies. Ante otro animal elige una de las tres con mucha seguridad;
  por eso el formulario permite marcar “Otro animal”.
- Cualquiera con el enlace puede registrar avistamientos (no hay inicio de sesión).
