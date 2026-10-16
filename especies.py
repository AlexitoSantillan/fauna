"""Datos fijos de la app: especies, provincias de Huánuco y líneas temáticas del INNOBEST."""

# La clave es el nombre de la carpeta (clase) con la que se entrenó el modelo.
ESPECIES = {
    "oso_de_anteojos": {
        "nombre": "Oso de anteojos",
        "cientifico": "Tremarctos ornatus",
        "estado": "Vulnerable",
        "color": "#b7860b",
        "dato": "Registrado con cámaras trampa en el Área de Conservación Regional "
                "Bosque Montano de Carpish, en Huánuco. Es el oso emblemático de la región.",
    },
    "mono_choro_cola_amarilla": {
        "nombre": "Mono choro de cola amarilla",
        "cientifico": "Lagothrix flavicauda",
        "estado": "En peligro crítico",
        "color": "#c62828",
        "dato": "Primate endémico del Perú. Se estima una pérdida de hábitat de cerca del 81 % "
                "por deforestación y fragmentación. En Huánuco se registró en la cuenca del río Chontayacu.",
    },
    "mono_arana_negro": {
        "nombre": "Mono araña de cara negra",
        "cientifico": "Ateles chamek",
        "estado": "En peligro",
        "color": "#e65100",
        "dato": "Su población habría caído al menos 50 % en 45 años. "
                "En Huánuco se registró en el alto Huallaga.",
    },
}

# Opción para el usuario cuando el modelo se equivoca o no es ninguna de las 3 especies.
OTRO = {
    "nombre": "Otro animal / no estoy seguro",
    "cientifico": "",
    "estado": "",
    "color": "#6b7280",
    "dato": "",
}

# Orden alfabético de las carpetas = orden de las clases del modelo entrenado.
CLASES_POR_DEFECTO = ["mono_arana_negro", "mono_choro_cola_amarilla", "oso_de_anteojos"]

PROVINCIAS = [
    "Huánuco", "Ambo", "Dos de Mayo", "Huacaybamba", "Huamalíes", "Leoncio Prado",
    "Marañón", "Pachitea", "Puerto Inca", "Lauricocha", "Yarowilca",
]

LINEAS = [
    ("Línea 3", "Conservación de la biodiversidad y protección de fauna silvestre",
     "La app identifica con inteligencia artificial mamíferos amenazados a partir de una foto "
     "y permite registrar dónde fueron vistos."),
    ("Línea 4", "Tecnologías de la información y monitoreo ambiental aplicado",
     "Cada avistamiento queda guardado en una base de datos (MongoDB) y alimenta un panel de "
     "monitoreo abierto a cualquier persona."),
]


def info(clave):
    """Ficha de una especie; si la clave no existe devuelve una ficha genérica."""
    if clave in ESPECIES:
        return ESPECIES[clave]
    if clave == "otro":
        return OTRO
    return {"nombre": str(clave).replace("_", " ").capitalize(), "cientifico": "",
            "estado": "", "color": "#2e7d32", "dato": ""}
