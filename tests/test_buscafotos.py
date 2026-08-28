"""Pruebas del buscador de fotos.

Usa fotos de mentira y una lectura simulada, así que no necesita llave de la
API ni gasta saldo.
"""

import base64
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from buscafotos import ajustes, cli, indice, vision  # noqa: E402

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


class PruebaBuscafotos(unittest.TestCase):
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

    def test_carpetas_lista_las_subcarpetas_con_fotos(self):
        codigo, texto = self.correr("carpetas")
        self.assertEqual(codigo, 0)
        self.assertIn("01 Macabeadas Grandes", texto)
        self.assertIn("05 Macabeadas Chicos", texto)

    def test_indexar_respeta_el_filtro_de_carpetas(self):
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
        codigo, texto = self.correr("buscar", "antorcha")
        self.assertEqual(codigo, 0)
        copiadas = list((self.elegidas / "antorcha").glob("*.jpg"))
        self.assertEqual(len(copiadas), 1)
        self.assertEqual(copiadas[0].read_bytes(), JPEG)

    def test_solo_mirar_no_copia_nada(self):
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


class PruebaRelevancia(unittest.TestCase):
    """La búsqueda tiene que aguantar plurales, tildes y sinónimos."""

    def setUp(self):
        self.datos = {"fotos": [dict(f, id=str(n), carpeta="Chicos")
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
