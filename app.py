"""App web INNOBEST Huánuco 2026: identifica mamíferos amenazados de Huánuco con IA
y guarda los avistamientos en MongoDB.

Ejecutar en local:   python app.py
En Render:           gunicorn app:app
"""
import base64
import io
import json
import os
from datetime import datetime, timedelta, timezone

from flask import Flask, abort, jsonify, redirect, render_template, request, url_for
from PIL import Image, UnidentifiedImageError

from db import Almacen
from especies import ESPECIES, LINEAS, OTRO, PROVINCIAS, info

Image.MAX_IMAGE_PIXELS = 40_000_000
UMBRAL_SEGURIDAD = 0.60
LIMA = timezone(timedelta(hours=-5))      # Perú no usa horario de verano


def miniatura_b64(img, lado=480):
    """Foto reducida (JPEG) en base64, para guardarla dentro del documento de MongoDB."""
    img = img.convert("RGB")
    img.thumbnail((lado, lado))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=80)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def validar_foto_b64(texto):
    """Acepta solo un JPEG pequeño en base64 (el formulario lo manda en un campo oculto)."""
    if not texto:
        return ""
    if len(texto) > 300_000:
        raise ValueError("foto demasiado grande")
    try:
        im = Image.open(io.BytesIO(base64.b64decode(texto, validate=True)))
        formato = im.format
        im.verify()
    except Exception:
        raise ValueError("foto inválida")
    if formato != "JPEG":
        raise ValueError("foto inválida")
    return texto


def crear_app(clasificador=None, almacen=None):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024        # fotos de hasta 8 MB
    modelo = {"clf": clasificador, "error": None}
    datos = almacen or Almacen(os.environ.get("MONGODB_URI"), os.environ.get("MONGODB_DB", "innobest"))

    def obtener_clasificador():
        if modelo["clf"] is None and modelo["error"] is None:
            try:
                from modelo import Clasificador
                modelo["clf"] = Clasificador()
            except Exception as e:
                modelo["error"] = f"{type(e).__name__}: {e}"
        return modelo["clf"]

    @app.context_processor
    def contexto():
        return {"db_modo": datos.modo, "ESPECIES": ESPECIES, "OTRO": OTRO, "info": info}

    @app.template_filter("fecha")
    def fecha(dt):
        return dt.replace(tzinfo=timezone.utc).astimezone(LIMA).strftime("%d/%m/%Y %H:%M")

    # ------------------------------------------------------------ páginas
    @app.route("/")
    def inicio():
        conteos = datos.conteos()
        return render_template("inicio.html", lineas=LINEAS, total=sum(conteos.values()),
                               conteos=conteos)

    @app.route("/identificar", methods=["GET", "POST"])
    def identificar():
        plantilla = "identificar.html"
        if request.method == "GET":
            return render_template(plantilla, resultado=None, error=None, provincias=PROVINCIAS)

        archivo = request.files.get("foto")
        if not archivo or not archivo.filename:
            return render_template(plantilla, resultado=None, provincias=PROVINCIAS,
                                   error="Elige una foto primero.")
        try:
            img = Image.open(archivo.stream)
            img.load()
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
            return render_template(plantilla, resultado=None, provincias=PROVINCIAS,
                                   error="No pude leer esa imagen. Prueba con un JPG o PNG.")
        clf = obtener_clasificador()
        if clf is None:
            return render_template(plantilla, resultado=None, provincias=PROVINCIAS,
                                   error=f"El modelo no está disponible ({modelo['error']}).")

        items = clf.predecir(img)
        foto = miniatura_b64(img)
        top, prob = items[0]
        resultado = {
            "items": [{"clave": k, "p": p, "pct": f"{p * 100:.1f}", **info(k)} for k, p in items],
            "top": top, "prob": prob, "pct": f"{prob * 100:.1f}",
            "poca_seguridad": prob < UMBRAL_SEGURIDAD,
            "foto": foto,
            "probs_json": json.dumps({k: round(p, 4) for k, p in items}),
        }
        return render_template(plantilla, resultado=resultado, error=None, provincias=PROVINCIAS)

    @app.post("/guardar")
    def guardar():
        f = request.form
        final = f.get("especie_final", "")
        pred = f.get("pred", "")
        provincia = f.get("provincia", "")
        if final not in ESPECIES and final != "otro":
            abort(400)
        if pred not in ESPECIES:
            abort(400)
        if provincia not in PROVINCIAS:
            abort(400)
        try:
            confianza = min(1.0, max(0.0, float(f.get("confianza", "0"))))
            foto = validar_foto_b64(f.get("foto", ""))
            crudo = json.loads(f.get("probs", "{}"))
            probs = {k: min(1.0, max(0.0, float(v))) for k, v in crudo.items() if k in ESPECIES}
        except (ValueError, TypeError, AttributeError):
            abort(400)
        doc = {
            "especie_modelo": pred,
            "especie_final": final,
            "confirmada_por_usuario": final != pred,
            "confianza": confianza,
            "probabilidades": probs,
            "provincia": provincia,
            "referencia": f.get("referencia", "").strip()[:120],
            "observador": f.get("observador", "").strip()[:60],
            "notas": f.get("notas", "").strip()[:500],
            "foto_b64": foto,
        }
        datos.guardar(doc)
        return redirect(url_for("registros", guardado=1))

    @app.route("/registros")
    def registros():
        especie = request.args.get("especie")
        if especie not in ESPECIES and especie != "otro":
            especie = None
        conteos = datos.conteos()
        return render_template("registros.html", docs=datos.listar(especie), especie=especie,
                               conteos=conteos, total=sum(conteos.values()),
                               guardado=request.args.get("guardado"))

    @app.post("/api/identificar")
    def api_identificar():
        archivo = request.files.get("foto")
        if not archivo:
            return jsonify(error="Falta la foto"), 400
        try:
            img = Image.open(archivo.stream)
            img.load()
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
            return jsonify(error="Imagen no válida"), 400
        clf = obtener_clasificador()
        if clf is None:
            return jsonify(error="Modelo no disponible"), 503
        items = clf.predecir(img)
        top, prob = items[0]
        return jsonify(
            top=top,
            nombre=info(top)["nombre"],
            color=info(top)["color"],
            pct=round(prob * 100, 1),
            poca_seguridad=prob < UMBRAL_SEGURIDAD,
            items=[{"nombre": info(k)["nombre"], "color": info(k)["color"],
                    "pct": round(p * 100, 1)} for k, p in items],
        )

    # ------------------------------------------------------------ API y estado
    @app.route("/api/avistamientos")
    def api_avistamientos():
        filas = []
        for d in datos.listar(limite=200):
            filas.append({
                "id": d["id"], "creado": d["creado"].isoformat() + "Z",
                "especie": d["especie_final"], "especie_modelo": d["especie_modelo"],
                "confianza": d["confianza"], "provincia": d["provincia"],
                "referencia": d.get("referencia", ""), "notas": d.get("notas", ""),
            })
        return jsonify(filas)

    @app.route("/api/estadisticas")
    def api_estadisticas():
        conteos = datos.conteos()
        return jsonify({"total": sum(conteos.values()), "por_especie": conteos})

    @app.route("/salud")
    def salud():
        obtener_clasificador()
        return jsonify({
            "modelo": "ok" if modelo["clf"] else f"error: {modelo['error']}",
            "base_de_datos": datos.modo,
            "error_base_de_datos": datos.error,
        })

    @app.errorhandler(413)
    def muy_grande(_):
        return render_template("identificar.html", resultado=None, provincias=PROVINCIAS,
                               error="La foto pesa demasiado (máximo 8 MB)."), 413

    return app


app = crear_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)