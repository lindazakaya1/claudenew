"""Pruebas de la cola de publicaciones."""

import json
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from programador import cola, config  # noqa: E402


class PruebaCola(unittest.TestCase):
    def setUp(self):
        self.temporal = TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        raiz = Path(self.temporal.name)

        self.programados = raiz / "programados"
        self.publicados = raiz / "publicados"
        self.programados.mkdir()

        self._original = (config.DIR_PROGRAMADOS, config.DIR_PUBLICADOS)
        config.DIR_PROGRAMADOS = self.programados
        config.DIR_PUBLICADOS = self.publicados
        self.addCleanup(self._restaurar)

    def _restaurar(self):
        config.DIR_PROGRAMADOS, config.DIR_PUBLICADOS = self._original

    def _programar(self, texto, cuando):
        return cola.crear(
            texto=texto, cuando=cuando, imagen_url="https://ejemplo.com/f.jpg"
        )

    def test_fecha_sin_zona_usa_la_del_config(self):
        fecha = cola.parsear_fecha("2026-08-21 10:00")
        self.assertIsNotNone(fecha.tzinfo)
        self.assertEqual((fecha.hour, fecha.minute), (10, 0))

    def test_fecha_con_zona_se_respeta(self):
        fecha = cola.parsear_fecha("2026-08-21T10:00:00+02:00")
        self.assertEqual(fecha.utcoffset(), timedelta(hours=2))

    def test_crear_guarda_el_json(self):
        ruta, pub = self._programar("Buenos días ☀️", "2026-08-21 10:00")
        self.assertTrue(ruta.exists())
        guardado = json.loads(ruta.read_text(encoding="utf-8"))
        self.assertEqual(guardado["texto"], "Buenos días ☀️")
        self.assertEqual(guardado["estado"], "programado")
        self.assertEqual(pub["redes"], ["instagram"])

    def test_rechaza_imagen_y_url_a_la_vez(self):
        with self.assertRaises(ValueError):
            cola.crear(
                texto="x",
                cuando="2026-08-21 10:00",
                imagen="fotos/a.jpg",
                imagen_url="https://ejemplo.com/f.jpg",
            )

    def test_rechaza_red_desconocida(self):
        with self.assertRaises(ValueError):
            cola.crear(
                texto="x",
                cuando="2026-08-21 10:00",
                imagen_url="https://ejemplo.com/f.jpg",
                redes=["tiktok"],
            )

    def test_pendientes_solo_devuelve_las_vencidas(self):
        ahora = datetime.now(config.zona_horaria())
        self._programar("ya toca", (ahora - timedelta(minutes=5)).isoformat())
        self._programar("todavia no", (ahora + timedelta(days=1)).isoformat())

        vencidas = cola.pendientes(ahora)
        self.assertEqual(len(vencidas), 1)
        self.assertEqual(vencidas[0][1]["texto"], "ya toca")

    def test_listar_ordena_por_fecha(self):
        self._programar("segunda", "2026-08-22 10:00")
        self._programar("primera", "2026-08-21 10:00")
        textos = [pub["texto"] for _, pub in cola.listar()]
        self.assertEqual(textos, ["primera", "segunda"])

    def test_archivar_mueve_y_deja_constancia(self):
        ruta, pub = self._programar("adios", "2026-08-21 10:00")
        destino = cola.archivar(ruta, pub, {"recordatorio": "abc123"})

        self.assertFalse(ruta.exists())
        self.assertTrue(destino.exists())
        guardado = json.loads(destino.read_text(encoding="utf-8"))
        self.assertEqual(guardado["estado"], "publicado")
        self.assertEqual(guardado["resultados"], {"recordatorio": "abc123"})

    def test_marcar_error_conserva_la_publicacion(self):
        ruta, pub = self._programar("falla", "2026-08-21 10:00")
        cola.marcar_error(ruta, pub, "sin internet")

        guardado = json.loads(ruta.read_text(encoding="utf-8"))
        self.assertEqual(guardado["ultimo_error"], "sin internet")
        self.assertEqual(guardado["intentos"], 1)
        self.assertEqual(guardado["estado"], "programado")


class PruebaRecordatorio(unittest.TestCase):
    def test_cabecera_ascii_no_se_toca(self):
        from programador.recordatorio import _cabecera

        self.assertEqual(_cabecera("Hola"), "Hola")

    def test_cabecera_con_acentos_se_codifica(self):
        from programador.recordatorio import _cabecera

        codificada = _cabecera("Buenos días ☀️")
        self.assertTrue(codificada.startswith("=?utf-8?"))

    def test_nombre_de_archivo_se_limpia(self):
        from programador.recordatorio import _nombre_seguro

        self.assertEqual(_nombre_seguro("mi foto ñ.jpg"), "mi_foto__.jpg")


if __name__ == "__main__":
    unittest.main()
