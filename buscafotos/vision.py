"""Mira una foto y escribe qué se ve en ella, usando la API de Claude."""

import base64
import json
import re
import time
import urllib.error
import urllib.request

from . import ajustes

URL_API = "https://api.anthropic.com/v1/messages"
VERSION_API = "2023-06-01"

INSTRUCCION = """Mira esta foto de un evento deportivo juvenil y descríbela para
un banco de imágenes que usará una diseñadora gráfica.

Responde SOLO con un objeto JSON, sin texto antes ni después, con estas claves:

- "descripcion": una o dos frases en español diciendo qué se ve. Concreto:
  quién aparece, qué hace, dónde está.
- "etiquetas": entre 12 y 20 palabras clave en español, en minúsculas. Incluye
  SINÓNIMOS de cada cosa importante, porque quien busque puede usar otra
  palabra: si hay una antorcha pon también "fuego", "llama", "fogata";
  si hay un niño pon también "nino", "chico", "muchacho", "joven".
  Etiqueta también las emociones ("sonriendo", "alegria", "concentracion"),
  la acción ("corriendo", "saltando", "abrazo", "premiacion"), el lugar
  ("cancha", "gimnasio", "exterior", "noche") y los colores dominantes.
- "personas": número aproximado de personas visibles (0 si no hay ninguna).
- "edades": una de "ninos", "adolescentes", "adultos", "mezcla" o "ninguna".
- "orientacion": "vertical", "horizontal" o "cuadrada".
- "espacio_para_texto": dónde hay una zona despejada donde cabría un titular:
  "arriba", "abajo", "izquierda", "derecha", "centro" o "ninguno".
- "calidad": "buena", "regular" o "mala" (borrosa, mal encuadrada, oscura).

Escribe las etiquetas sin tildes."""


class ErrorVision(Exception):
    """Algo salió mal al pedirle a Claude que mirara la foto."""


def _pedir(cuerpo, clave, intentos=4):
    """Llama a la API reintentando cuando el servidor está saturado."""
    datos = json.dumps(cuerpo).encode("utf-8")
    espera = 2
    for intento in range(1, intentos + 1):
        pedido = urllib.request.Request(URL_API, data=datos, method="POST")
        pedido.add_header("content-type", "application/json")
        pedido.add_header("x-api-key", clave)
        pedido.add_header("anthropic-version", VERSION_API)
        try:
            with urllib.request.urlopen(pedido, timeout=120) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detalle = e.read().decode("utf-8", "replace")[:300]
            # 429 = demasiadas peticiones seguidas, 5xx = problema pasajero.
            # Cualquier otro código (401 llave mala, 400 petición mal armada)
            # no se arregla reintentando.
            if e.code not in (429, 500, 502, 503, 529) or intento == intentos:
                raise ErrorVision(f"HTTP {e.code}: {detalle}") from e
        except urllib.error.URLError as e:
            if intento == intentos:
                raise ErrorVision(f"sin conexión: {e.reason}") from e
        time.sleep(espera)
        espera *= 2
    raise ErrorVision("no hubo respuesta")


def _extraer_json(texto):
    """El JSON de la respuesta, aunque venga envuelto en ```json ... ```."""
    texto = texto.strip()
    if texto.startswith("```"):
        texto = re.sub(r"^```[a-z]*\s*|\s*```$", "", texto)
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", texto, re.S)
        if not m:
            raise ErrorVision(f"la respuesta no traía JSON: {texto[:200]}")
        return json.loads(m.group(0))


def describir(imagen, tipo="image/jpeg", clave=None, modelo=None):
    """Devuelve el diccionario con la descripción y las etiquetas de una foto.

    `imagen` son los bytes crudos del archivo.
    """
    clave = clave or ajustes.clave_api()
    if not clave:
        raise ErrorVision(
            "falta la llave de la API. Ponla en la variable ANTHROPIC_API_KEY "
            "o en el archivo buscafotos/clave.txt"
        )
    modelo = modelo or ajustes.cargar()["modelo"]

    respuesta = _pedir(
        {
            "model": modelo,
            "max_tokens": 700,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": tipo,
                                "data": base64.b64encode(imagen).decode("ascii"),
                            },
                        },
                        {"type": "text", "text": INSTRUCCION},
                    ],
                }
            ],
        },
        clave,
    )

    partes = [b.get("text", "") for b in respuesta.get("content", []) if b.get("type") == "text"]
    ficha = _extraer_json("".join(partes))

    # Se normaliza lo que vuelve para que el índice sea siempre igual, aunque
    # el modelo devuelva una etiqueta suelta como texto en vez de lista.
    etiquetas = ficha.get("etiquetas", [])
    if isinstance(etiquetas, str):
        etiquetas = [e.strip() for e in etiquetas.split(",")]
    ficha["etiquetas"] = [str(e).strip().lower() for e in etiquetas if str(e).strip()]
    ficha["descripcion"] = str(ficha.get("descripcion", "")).strip()
    return ficha
