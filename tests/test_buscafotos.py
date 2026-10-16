"""Pruebas del buscador de fotos.

Usa fotos de mentira y una lectura simulada, así que no necesita llave de la
API, no gasta saldo y no toca internet.
"""

import base64
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from buscafotos import ajustes, cli, indice, pictime, vision  # noqa: E402

# JPEG de 1x1 píxel: el contenido da igual porque la lectura está simulada.
JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0a"
    "HBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAA"
    "AAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AVN//2Q=="
)

FICHAS = [
    {
        "descripcion": "Un niño sonriendo sostiene una antorcha encendida de noche.",
        "etiquetas": ["nino", "antorcha", "fuego", "llama", "sonriendo", "noche"],
        "personas": 1, "edades": "ninos", "orientacion": "vertical",
        "espacio_para_texto": "arriba", "calidad": "buena",
    },
    {
        "descripcion": "Equipo juvenil celebrando en la cancha con los brazos arriba.",
        "etiquetas": ["equipo", "celebracion", "cancha", "alegria", "adolescentes"],
        "personas": 8, "edades": "adolescentes", "orientacion": "horizontal",
        "espacio_para_texto": "abajo", "calidad": "buena",
    },
    {
        "descripcion": "Trofeo dorado sobre una mesa con fondo azul.",
        "etiquetas": ["trofeo", "premio", "copa", "dorado", "azul"],
        "personas": 0, "edades": "ninguna", "orientacion": "cuadrada",
        "espacio_para_texto": "derecha", "calidad": "buena",
    },
]


class PruebaCarpetaLocal(unittest.TestCase):
    """El modo que lee de una carpeta de la computadora."""

    def setUp(self):
        self.temporal = TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        raiz = Path(self.temporal.name)

        self.fotos = raiz / "Macabeadas"
        for carpeta, archivos in {
            "01 Macabeadas Grandes": ["a1.jpg", "a2.jpg"],
            "05 Macabeadas Chicos": ["b1.jpg", "b2.jpg", "b3.jpg"],
        }.items():
            (self.fotos / carpeta).mkdir(parents=True)
            for nombre in archivos:
                (self.fotos / carpeta / nombre).write_bytes(JPEG)

        self.elegidas = raiz / "elegidas"
        self._original = (ajustes.ARCHIVO_AJUSTES, ajustes.ARCHIVO_INDICE, vision.describir)
        ajustes.ARCHIVO_AJUSTES = raiz / "ajustes.json"
        ajustes.ARCHIVO_INDICE = raiz / "indice.json"
        ajustes.guardar({
            "origen": "carpeta",
            "galeria": "https://ejemplo.pic-time.com",
            "carpeta_local": str(self.fotos),
            "carpetas": ["chicos"],
            "destino": str(self.elegidas),
            "modelo": "modelo-de-prueba",
            "cuantas": 2,
        })

        self.leidas = 0

        def lectura_simulada(imagen, tipo="image/jpeg", clave=None, modelo=None):
            ficha = dict(FICHAS[self.leidas % len(FICHAS)])
            self.leidas += 1
            return ficha

        vision.describir = lectura_simulada
        self.addCleanup(self._restaurar)

    def _restaurar(self):
        ajustes.ARCHIVO_AJUSTES, ajustes.ARCHIVO_INDICE, vision.describir = self._original

    def correr(self, *argumentos):
        """Ejecuta un comando y devuelve (código de salida, lo que imprimió)."""
        salida = io.StringIO()
        with redirect_stdout(salida):
            codigo = cli.main(list(argumentos))
        return codigo, salida.getvalue()

    def test_carpetas_marca_las_elegidas(self):
        codigo, texto = self.correr("carpetas")
        self.assertEqual(codigo, 0)
        self.assertIn("01 Macabeadas Grandes", texto)
        self.assertIn("05 Macabeadas Chicos", texto)
        for linea in texto.splitlines():
            if "Chicos" in linea:
                self.assertTrue(linea.lstrip().startswith("*"), linea)
            if "Grandes" in linea:
                self.assertFalse(linea.lstrip().startswith("*"), linea)

    def test_indexar_respeta_el_filtro(self):
        self.assertEqual(self.correr("indexar")[0], 0)
        fotos = indice.cargar()["fotos"]
        self.assertEqual(len(fotos), 3)
        for foto in fotos:
            self.assertIn("chicos", foto["carpeta"].lower())

    def test_indexar_dos_veces_no_repite_trabajo(self):
        self.correr("indexar")
        leidas = self.leidas
        codigo, texto = self.correr("indexar")
        self.assertEqual(codigo, 0)
        self.assertEqual(self.leidas, leidas, "volvió a mirar fotos ya indexadas")
        self.assertIn("al día", texto)

    def test_indexar_con_limite(self):
        self.assertEqual(self.correr("indexar", "--limite", "2")[0], 0)
        self.assertEqual(len(indice.cargar()["fotos"]), 2)

    def test_buscar_copia_la_foto_pedida(self):
        self.correr("indexar")
        self.assertEqual(self.correr("buscar", "antorcha")[0], 0)
        copiadas = list((self.elegidas / "antorcha").glob("*.jpg"))
        self.assertEqual(len(copiadas), 1)
        self.assertEqual(copiadas[0].read_bytes(), JPEG)

    def test_solo_mirar_no_trae_nada(self):
        self.correr("indexar")
        codigo, texto = self.correr("buscar", "trofeo", "--solo-mirar")
        self.assertEqual(codigo, 0)
        self.assertIn("Trofeo", texto)
        self.assertFalse((self.elegidas / "trofeo").exists())

    def test_buscar_sin_resultados_avisa(self):
        self.correr("indexar")
        codigo, texto = self.correr("buscar", "elefante")
        self.assertEqual(codigo, 1)
        self.assertIn("No encontré nada", texto)

    def test_buscar_sin_indice_avisa(self):
        codigo, texto = self.correr("buscar", "antorcha")
        self.assertEqual(codigo, 1)
        self.assertIn("índice está vacío", texto)


class PruebaPicTime(unittest.TestCase):
    """El lector de la galería en la web, con respuestas de mentira.

    Las respuestas reproducen la forma real que tienen los datos de
    Pic-Time, incluidos los identificadores guardados como diferencias
    contra minId y las fichas de cinco campos por foto.
    """

    PORTADA = (
        '<html><script>var initParams = {"accountId":518023,"accountStorageId":102,'
        '"portfolioId":"abc123","portfolioTS":1784741338};</script>'
        '<script>_pictimeStorageMapping = ['
        '{"storageId":102,"dataDomain":"https://datos.ejemplo","cdnDomain":"https://cuenta.ejemplo"},'
        '{"storageId":18,"dataDomain":"https://datos18.ejemplo","cdnDomain":"https://proyecto.ejemplo"}'
        '];</script></html>'
    )

    PORTAFOLIO = json.dumps([None, [
        "abc123", None, 10,
        [
            [None, [50350259, "VIII Macabeadas Juveniles | Domingo 18",
                    "viiijuvenilesdomingo18", "homepage.jpg", "50,50", 0.667]],
            [None, [52853879, "MN 2026 | Premiaciones",
                    "mn-2026--premiaciones", "homepage.jpg", "50,50", 0.667]],
        ],
    ]])

    PAGINA_CARPETA = (
        '<html><script>var initParams = {"projectId":50350259,'
        '"projectStorageId":18,"projectPathToken":"tok123"};</script></html>'
    )

    LISTADO = json.dumps({
        "version": 3,
        "minId": 11624855557,
        "scenes": [
            # Dos fotos: 1888201 y 1888202 de diferencia contra minId.
            {"name": "Scene 1", "photos": [1888201, 0, 0, 0, 0,
                                           1888202, 0, 0, 132, 34]},
            {"name": "Scene 2", "photos": [885925, 0, 0, 0, 0]},
        ],
    })

    def setUp(self):
        self.pedidos = []
        # Tamaños que esta galería de mentira no tiene.
        self.faltantes = ()
        self._traer = pictime._traer

        def traer_simulado(url, que=""):
            self.pedidos.append(url)
            if url.endswith("/portfolio"):
                return self.PORTADA.encode()
            if "portfolio.json.txt" in url:
                return self.PORTAFOLIO.encode()
            if "/-viiijuvenilesdomingo18" in url:
                return self.PAGINA_CARPETA.encode()
            if "gallery.json.txt" in url:
                return self.LISTADO.encode()
            if url.endswith(".jpg"):
                if any(f"/{t}/" in url for t in self.faltantes):
                    raise pictime.ErrorGaleria(f"HTTP 404 al pedir {url}")
                return JPEG
            raise pictime.ErrorGaleria(f"no simulado: {url}")

        pictime._traer = traer_simulado
        self.addCleanup(lambda: setattr(pictime, "_traer", self._traer))

    def test_lista_las_carpetas(self):
        carpetas = pictime.listar_carpetas("https://ejemplo.pic-time.com")
        self.assertEqual(len(carpetas), 2)
        self.assertEqual(carpetas[0]["nombre"], "VIII Macabeadas Juveniles | Domingo 18")
        self.assertEqual(carpetas[0]["ruta"], "viiijuvenilesdomingo18")
        self.assertEqual(carpetas[0]["id"], 50350259)

    def test_los_identificadores_se_suman_a_minid(self):
        carpetas = pictime.listar_carpetas("https://ejemplo.pic-time.com")
        fotos = pictime.listar_fotos("https://ejemplo.pic-time.com", carpetas[0])
        # Dos fichas en la primera escena y una en la segunda.
        self.assertEqual(len(fotos), 3)
        self.assertEqual([f["foto"] for f in fotos],
                         [11626743758, 11626743759, 11625741482])

    def test_arma_bien_la_direccion_de_la_foto(self):
        carpetas = pictime.listar_carpetas("https://ejemplo.pic-time.com")
        fotos = pictime.listar_fotos("https://ejemplo.pic-time.com", carpetas[0])
        self.assertEqual(
            fotos[0]["url"],
            "https://proyecto.ejemplo/pictures/50/350/50350259/tok123/midres/11626743758.jpg")

    def test_baja_de_tamano_cuando_el_grande_no_existe(self):
        # La galería real solo sirve thumbres: midres y los demás dan 404.
        self.faltantes = ("midres", "lowres", "smallres", "thumbs")
        carpetas = pictime.listar_carpetas("https://ejemplo.pic-time.com")
        fotos = pictime.listar_fotos("https://ejemplo.pic-time.com", carpetas[0])
        self.assertEqual(fotos[0]["tamano"], "thumbres")
        self.assertIn("/thumbres/", fotos[0]["url"])

    def test_sin_ningun_tamano_avisa_claro(self):
        self.faltantes = pictime.TAMANOS
        carpetas = pictime.listar_carpetas("https://ejemplo.pic-time.com")
        with self.assertRaises(pictime.ErrorGaleria) as caja:
            pictime.listar_fotos("https://ejemplo.pic-time.com", carpetas[0])
        self.assertIn("ningún tamaño", str(caja.exception))

    def test_siempre_trae_la_miniatura(self):
        carpetas = pictime.listar_carpetas("https://ejemplo.pic-time.com")
        fotos = pictime.listar_fotos("https://ejemplo.pic-time.com", carpetas[0])
        self.assertEqual(
            fotos[0]["url_thumb"],
            "https://proyecto.ejemplo/pictures/50/350/50350259/tok123/thumbres/11626743758.jpg")

    def test_la_ruta_de_la_cuenta_usa_dos_niveles(self):
        pictime.listar_carpetas("https://ejemplo.pic-time.com")
        ruta = next(u for u in self.pedidos if "portfolio.json.txt" in u)
        self.assertIn("/pictures/accountdata/518/518023/client/abc123/", ruta)

    def test_la_pagina_de_carpeta_lleva_guion(self):
        carpetas = pictime.listar_carpetas("https://ejemplo.pic-time.com")
        pictime.listar_fotos("https://ejemplo.pic-time.com", carpetas[0])
        self.assertTrue(any(u.endswith("/-viiijuvenilesdomingo18") for u in self.pedidos),
                        self.pedidos)

    def test_cada_foto_sale_una_sola_vez(self):
        carpetas = pictime.listar_carpetas("https://ejemplo.pic-time.com")
        fotos = pictime.listar_fotos("https://ejemplo.pic-time.com", carpetas[0])
        identificadores = [f["id"] for f in fotos]
        self.assertEqual(len(identificadores), len(set(identificadores)))

    def test_sin_minid_avisa_claro(self):
        listado = self.LISTADO
        self.LISTADO = json.dumps({"version": 3, "scenes": []})
        self.addCleanup(lambda: setattr(self, "LISTADO", listado))
        carpetas = pictime.listar_carpetas("https://ejemplo.pic-time.com")
        with self.assertRaises(pictime.ErrorGaleria) as caja:
            pictime.listar_fotos("https://ejemplo.pic-time.com", carpetas[0])
        self.assertIn("minId", str(caja.exception))


class PruebaTroceo(unittest.TestCase):
    """Pic-Time reparte los identificadores en carpetas, y no igual para todo."""

    def test_la_cuenta_usa_dos_niveles(self):
        self.assertEqual(pictime._ruta_de_cuenta(518023), "518/518023")

    def test_el_proyecto_usa_tres_niveles(self):
        self.assertEqual(pictime._ruta_de_proyecto(50350259), "50/350/50350259")
        self.assertEqual(pictime._ruta_de_proyecto(49569147), "49/569/49569147")


class PruebaRelevancia(unittest.TestCase):
    """La búsqueda tiene que aguantar plurales, tildes y sinónimos."""

    def setUp(self):
        self.datos = {"fotos": [dict(f, id=str(n), carpeta="Juveniles")
                                for n, f in enumerate(FICHAS)]}

    def _primera(self, consulta):
        resultados = indice.buscar(consulta, cuantas=3, datos=self.datos)
        self.assertTrue(resultados, f"«{consulta}» no devolvió nada")
        return resultados[0][1]["etiquetas"]

    def test_palabra_exacta(self):
        self.assertIn("antorcha", self._primera("antorcha"))

    def test_plural(self):
        self.assertIn("trofeo", self._primera("trofeos"))

    def test_tildes_y_enie(self):
        self.assertIn("antorcha", self._primera("niños sonriendo"))
        self.assertIn("antorcha", self._primera("nino sonriendo"))

    def test_sinonimo_de_la_etiqueta(self):
        self.assertIn("antorcha", self._primera("fuego"))

    def test_varias_palabras(self):
        self.assertIn("equipo", self._primera("celebracion equipo"))

    def test_palabras_de_relleno_no_estorban(self):
        self.assertIn("antorcha", self._primera("busca una foto de una antorcha"))


class PruebaLecturaDeRespuesta(unittest.TestCase):
    """El JSON de Claude se entiende venga limpio o envuelto."""

    esperado = {"descripcion": "Una antorcha.", "etiquetas": ["fuego"]}

    def test_json_pelado(self):
        crudo = '{"descripcion": "Una antorcha.", "etiquetas": ["fuego"]}'
        self.assertEqual(vision._extraer_json(crudo), self.esperado)

    def test_json_en_bloque_de_codigo(self):
        crudo = '```json\n{"descripcion": "Una antorcha.", "etiquetas": ["fuego"]}\n```'
        self.assertEqual(vision._extraer_json(crudo), self.esperado)

    def test_json_con_texto_antes(self):
        crudo = 'Claro:\n{"descripcion": "Una antorcha.", "etiquetas": ["fuego"]}'
        self.assertEqual(vision._extraer_json(crudo), self.esperado)

    def test_respuesta_sin_json_avisa(self):
        with self.assertRaises(vision.ErrorVision):
            vision._extraer_json("No puedo ver la imagen.")


if __name__ == "__main__":
    unittest.main()
