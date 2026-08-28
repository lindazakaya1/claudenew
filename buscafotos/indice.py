"""El índice: qué se ve en cada foto, y cómo buscar dentro de eso."""

import json
import unicodedata
from datetime import datetime, timezone

from . import ajustes

# Palabras que no aportan nada al buscar y solo generan ruido.
VACIAS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al",
    "y", "o", "que", "con", "sin", "en", "por", "para", "a", "es", "son",
    "foto", "fotos", "imagen", "imagenes", "busca", "buscame", "quiero",
    "dame", "necesito", "una", "algun", "alguna",
}


def normalizar(texto):
    """Minúsculas y sin tildes, para que 'niño' y 'nino' sean lo mismo."""
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def palabras(texto):
    limpio = "".join(c if c.isalnum() else " " for c in normalizar(texto))
    return [p for p in limpio.split() if len(p) > 2 and p not in VACIAS]


def _parecidas(a, b):
    """Cuánto se parecen dos palabras (0 a 1) comparando su raíz.

    En español las variantes comparten el principio: niño/niños,
    antorcha/antorchas, sonriendo/sonriente. Comparar el prefijo común
    evita tener que instalar un lematizador.
    """
    if a == b:
        return 1.0
    comun = 0
    for ca, cb in zip(a, b):
        if ca != cb:
            break
        comun += 1
    if comun < 4:
        return 0.0
    return comun / max(len(a), len(b))


def cargar():
    if not ajustes.ARCHIVO_INDICE.exists():
        return {"fotos": []}
    return json.loads(ajustes.ARCHIVO_INDICE.read_text("utf-8"))


def guardar(datos):
    datos["actualizado"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    ajustes.ARCHIVO_INDICE.write_text(
        json.dumps(datos, indent=1, ensure_ascii=False) + "\n", "utf-8"
    )


def texto_de(foto):
    """Todo lo que se sabe de una foto, junto, para poder buscar en ello."""
    partes = [foto.get("descripcion", ""), " ".join(foto.get("etiquetas", []))]
    partes.append(foto.get("carpeta", ""))
    return " ".join(partes)


def puntuar(foto, consulta):
    """Qué tan bien responde una foto a lo que se pidió."""
    buscadas = palabras(consulta)
    if not buscadas:
        return 0.0

    etiquetas = {normalizar(e) for e in foto.get("etiquetas", [])}
    del_texto = set(palabras(texto_de(foto)))

    total = 0.0
    for buscada in buscadas:
        # Una coincidencia en las etiquetas vale más que una en la descripción,
        # porque las etiquetas son lo que define la foto y la descripción
        # puede mencionar algo de pasada.
        mejor = 0.0
        for etiqueta in etiquetas:
            for palabra in etiqueta.split():
                mejor = max(mejor, _parecidas(buscada, palabra) * 1.0)
        for palabra in del_texto:
            mejor = max(mejor, _parecidas(buscada, palabra) * 0.6)
        total += mejor

    # Se divide entre lo pedido para que pedir muchas palabras no infle el
    # resultado: lo que importa es qué proporción de lo pedido aparece.
    return total / len(buscadas)


def buscar(consulta, cuantas=5, minimo=0.34, datos=None):
    """Las mejores fotos para una búsqueda, de mejor a peor."""
    datos = datos if datos is not None else cargar()
    marcadas = []
    for foto in datos.get("fotos", []):
        punto = puntuar(foto, consulta)
        if punto >= minimo:
            marcadas.append((punto, foto))
    marcadas.sort(key=lambda par: par[0], reverse=True)
    return marcadas[:cuantas]
