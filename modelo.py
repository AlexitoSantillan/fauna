"""Inferencia con el modelo entrenado (exportado a ONNX).

Se usa ONNX Runtime en lugar de PyTorch/Ultralytics porque es mucho más liviano y
entra en el plan gratuito de Render (512 MB de memoria).
"""
import ast
import os

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps

from especies import CLASES_POR_DEFECTO

RUTA_MODELO = os.environ.get(
    "MODEL_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "model", "best.onnx")
)


def preparar(img, tam=224):
    """Mismo preprocesado que Ultralytics para clasificación: lado corto a `tam`,
    recorte central, RGB, valores entre 0 y 1. Devuelve un arreglo (1, 3, tam, tam)."""
    img = ImageOps.exif_transpose(img).convert("RGB")
    w, h = img.size
    escala = tam / min(w, h)
    nw, nh = max(tam, round(w * escala)), max(tam, round(h * escala))
    img = img.resize((nw, nh), Image.BILINEAR)
    izq, arr = (nw - tam) // 2, (nh - tam) // 2
    img = img.crop((izq, arr, izq + tam, arr + tam))
    a = np.asarray(img, dtype=np.float32) / 255.0
    return a.transpose(2, 0, 1)[None]


def _softmax(x):
    e = np.exp(x - x.max())
    return e / e.sum()


class Clasificador:
    def __init__(self, ruta=RUTA_MODELO):
        if not os.path.exists(ruta):
            raise FileNotFoundError(f"No encuentro el modelo en {ruta}. Copia best.onnx a la carpeta model/.")
        self.sesion = ort.InferenceSession(ruta, providers=["CPUExecutionProvider"])
        entrada = self.sesion.get_inputs()[0]
        self.nombre_entrada = entrada.name
        forma = entrada.shape
        self.tam = forma[2] if len(forma) == 4 and isinstance(forma[2], int) else 224
        meta = self.sesion.get_modelmeta().custom_metadata_map
        self.clases = self._leer_clases(meta.get("names"))

    @staticmethod
    def _leer_clases(texto):
        """Ultralytics guarda los nombres como "{0: 'a', 1: 'b'}" dentro del .onnx."""
        try:
            d = ast.literal_eval(texto)
            return [d[i] for i in sorted(d)]
        except Exception:
            return list(CLASES_POR_DEFECTO)

    def predecir(self, img):
        """Devuelve [(clase, probabilidad)] ordenado de mayor a menor."""
        salida = self.sesion.run(None, {self.nombre_entrada: preparar(img, self.tam)})[0]
        p = np.asarray(salida, dtype=np.float64).reshape(-1)
        if (p < 0).any() or abs(p.sum() - 1.0) > 1e-3:  # si salieron logits, convertir
            p = _softmax(p)
        pares = [(self.clases[i], float(p[i])) for i in range(min(len(self.clases), len(p)))]
        return sorted(pares, key=lambda x: x[1], reverse=True)
