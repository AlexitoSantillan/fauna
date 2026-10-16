"""Convierte best.pt a best.onnx y comprueba que da las mismas respuestas.

Ejecutar en Colab (terminal), con best.pt y la carpeta dataset/ ya en /content:

    pip install -q ultralytics onnx onnxruntime
    python convertir_modelo.py best.pt dataset/val

Al final descarga best.onnx (aparece junto a best.pt) y cópialo a la carpeta model/ de la app.
"""
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps
from ultralytics import YOLO

pt = sys.argv[1] if len(sys.argv) > 1 else "best.pt"
carpeta_val = Path(sys.argv[2] if len(sys.argv) > 2 else "dataset/val")


def preparar(img, tam=224):
    """Debe ser igual a preparar() de modelo.py (la app)."""
    img = ImageOps.exif_transpose(img).convert("RGB")
    w, h = img.size
    escala = tam / min(w, h)
    nw, nh = max(tam, round(w * escala)), max(tam, round(h * escala))
    img = img.resize((nw, nh), Image.BILINEAR)
    izq, arr = (nw - tam) // 2, (nh - tam) // 2
    img = img.crop((izq, arr, izq + tam, arr + tam))
    a = np.asarray(img, dtype=np.float32) / 255.0
    return a.transpose(2, 0, 1)[None]


modelo = YOLO(pt)
ruta_onnx = modelo.export(format="onnx", imgsz=224, dynamic=False, simplify=False)
print("\nModelo exportado:", ruta_onnx)

sesion = ort.InferenceSession(str(ruta_onnx), providers=["CPUExecutionProvider"])
entrada = sesion.get_inputs()[0].name
nombres = modelo.names

fotos = sorted(p for p in carpeta_val.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
if not fotos:
    sys.exit(f"No encontré fotos en {carpeta_val}")

coinciden = aciertos_onnx = aciertos_pt = 0
for f in fotos:
    real = f.parent.name
    pred_pt = nombres[modelo.predict(str(f), verbose=False)[0].probs.top1]
    p = sesion.run(None, {entrada: preparar(Image.open(f))})[0].reshape(-1)
    pred_onnx = nombres[int(p.argmax())]
    coinciden += pred_pt == pred_onnx
    aciertos_pt += pred_pt == real
    aciertos_onnx += pred_onnx == real

n = len(fotos)
print(f"\nFotos revisadas:               {n}")
print(f"Aciertos con best.pt:          {aciertos_pt}/{n}")
print(f"Aciertos con best.onnx:        {aciertos_onnx}/{n}")
print(f"best.pt y best.onnx coinciden: {coinciden}/{n}")
print("\nSi coinciden en casi todas, el .onnx sirve. Descarga:", ruta_onnx)
