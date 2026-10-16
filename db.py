"""Almacenamiento de avistamientos: MongoDB si hay conexión; si no, memoria (modo local)."""
import threading
import time
from collections import Counter
from datetime import datetime, timezone


def ahora():
    """Fecha y hora UTC sin zona (así las devuelve MongoDB)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Almacen:
    def __init__(self, uri=None, db_nombre="innobest", cliente=None):
        self._uri = uri
        self._db_nombre = db_nombre
        self._lock = threading.Lock()
        self._memoria = []
        self._col = None
        self._ultimo_intento = 0.0
        self.error = None
        if cliente is not None:               # usado en las pruebas
            self._col = cliente[db_nombre]["avistamientos"]
        elif uri:
            self._conectar()

    # ------------------------------------------------------------ conexión
    def _conectar(self):
        self._ultimo_intento = time.time()
        try:
            from pymongo import MongoClient
            cliente = MongoClient(self._uri, serverSelectionTimeoutMS=5000)
            cliente.admin.command("ping")
            col = cliente[self._db_nombre]["avistamientos"]
            col.create_index([("creado", -1)])
            self._col, self.error = col, None
        except Exception as e:                 # nunca mostrar la URI (lleva la contraseña)
            self._col, self.error = None, type(e).__name__

    def _asegurar(self):
        """Si había URI pero no hubo conexión, reintenta como máximo una vez por minuto."""
        if self._col is None and self._uri and time.time() - self._ultimo_intento > 60:
            self._conectar()

    @property
    def modo(self):
        self._asegurar()
        return "mongodb" if self._col is not None else "memoria"

    # ------------------------------------------------------------ operaciones
    def guardar(self, doc):
        doc = dict(doc)
        doc.setdefault("creado", ahora())
        if self.modo == "mongodb":
            try:
                return str(self._col.insert_one(doc).inserted_id)
            except Exception as e:
                self._col, self.error = None, type(e).__name__
                doc.pop("_id", None)
        with self._lock:
            doc["_id"] = f"m{len(self._memoria) + 1}"
            self._memoria.append(doc)
            return doc["_id"]

    def listar(self, especie=None, limite=48):
        filtro = {"especie_final": especie} if especie else {}
        if self.modo == "mongodb":
            try:
                docs = list(self._col.find(filtro).sort("creado", -1).limit(limite))
                return [{**d, "id": str(d.pop("_id"))} for d in docs]
            except Exception as e:
                self._col, self.error = None, type(e).__name__
        with self._lock:
            docs = [d for d in self._memoria if not especie or d["especie_final"] == especie]
        docs = sorted(docs, key=lambda d: d["creado"], reverse=True)[:limite]
        return [{**d, "id": d["_id"]} for d in docs]

    def conteos(self):
        """{clave_especie: cantidad de avistamientos}"""
        if self.modo == "mongodb":
            try:
                filas = self._col.aggregate([{"$group": {"_id": "$especie_final", "n": {"$sum": 1}}}])
                return {f["_id"]: f["n"] for f in filas}
            except Exception as e:
                self._col, self.error = None, type(e).__name__
        with self._lock:
            return dict(Counter(d["especie_final"] for d in self._memoria))

    def total(self):
        return sum(self.conteos().values())
