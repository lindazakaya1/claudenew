import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from programador import cola, config

BOGOTA = ZoneInfo("America/Bogota")


class PruebaCola(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dirs_originales = (config.DIR_PROGRAMADOS, config.DIR_PUBLICADOS)
        config.DIR_PROGRAMADOS = Path(self.tmp.name) / "programados"
        config.DIR_PUBLICADOS = Path(self.tmp.name) / "publicados"
        config.DIR_PROGRAMADOS.mkdir()

    def tearDown(self):
        config.DIR_PROGRAMADOS, config.DIR_PUBLICADOS = self.dirs_originales
        self.tmp.cleanup()

    def test_fecha_sin_zona_usa_la_del_config(self):
        fecha = cola.parsear_fecha("2026-08-21 10:00")
        self.assertIsNotNone(fecha.tzinfo)
        self.assertEqual(fecha.hour, 10)

    def test_fecha_con_zona_se_respeta(self):
        fecha = cola.parsear_fecha("2026-08-21T10:00:00+02:00")
        self.assertEqual(fecha.utcoffset().total_seconds(), 7200)

    def test_crear_guarda_el_json(self):
        ruta, pub = cola.crear(
            texto="Hola mundo",
            cuando="2026-08-21 10:00",
            imagen_url="https://ejemplo.com/foto.jpg",
            redes=["instagram"],
        )
        self.assertTrue(ruta.exists())
        guardado = json.loads(ruta.read_text(encoding="utf-8"))
        self.assertEqual(guardado["texto"], "Hola mundo")
        self.assertEqual(guardado["estado"], "programado")
        self.assertEqual(pub["redes"], ["instagram"])

    def test_crear_exige_una_imagen(self):
        with self.assertRaises(ValueError):
            cola.crear(texto="Sin foto", cuando="2026-08-21 10:00")

    def test_crear_rechaza_redes_desconocidas(self):
        with self.assertRaises(ValueError):
            cola.crear(
                texto="Hola",
                cuando="2026-08-21 10:00",
                imagen_url="https://ejemplo.com/foto.jpg",
                redes=["tiktok"],
            )

    def test_pendientes_solo_devuelve_las_vencidas(self):
        cola.crear(
            texto="Ya toca",
            cuando="2026-08-21 10:00",
            imagen_url="https://ejemplo.com/a.jpg",
            redes=["instagram"],
        )
        cola.crear(
            texto="Todavia no",
            cuando="2026-08-21 18:00",
            imagen_url="https://ejemplo.com/b.jpg",
            redes=["instagram"],
        )
        ahora = datetime(2026, 8, 21, 11, 0, tzinfo=BOGOTA)
        vencidas = cola.pendientes(ahora)
        self.assertEqual([p["texto"] for _, p in vencidas], ["Ya toca"])

    def test_archivar_mueve_y_deja_constancia(self):
        ruta, pub = cola.crear(
            texto="Publicada",
            cuando="2026-08-21 10:00",
            imagen_url="https://ejemplo.com/a.jpg",
            redes=["instagram"],
        )
        destino = cola.archivar(ruta, pub, {"instagram": "123"})
        self.assertFalse(ruta.exists())
        guardado = json.loads(destino.read_text(encoding="utf-8"))
        self.assertEqual(guardado["estado"], "publicado")
        self.assertEqual(guardado["resultados"]["instagram"], "123")

    def test_url_de_imagen_desde_archivo_del_repo(self):
        url = cola.url_de_imagen({"imagen": "fotos/playa.jpg"})
        self.assertTrue(url.startswith("https://raw.githubusercontent.com/"))
        self.assertTrue(url.endswith("/fotos/playa.jpg"))


if __name__ == "__main__":
    unittest.main()
