"""Pruebas de ampliación editorial y territorial de La Gaceta Negra."""
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import actualizar as g


class TestRefuerzo(unittest.TestCase):
    def test_timos_y_suplantaciones(self):
        self.assertEqual(g.category("Detenido por una estafa mediante smishing bancario", "AUTO"), "TRUE CRIME")
        temas = g.topics_of("Detenido por una estafa de smishing bancario", "TRUE CRIME")
        self.assertIn("Estafas y fraudes", temas)
        self.assertIn("Timos y suplantaciones", temas)
        self.assertIn("Ciberdelincuencia", temas)

    def test_criminologia_y_forense(self):
        self.assertEqual(g.category("Publican una investigación criminológica sobre reincidencia", "AUTO"), "CRIME SCENE")
        temas = g.topics_of("La investigación criminológica analiza reincidencia y victimología", "CRIME SCENE")
        self.assertIn("Criminología", temas)
        self.assertIn("Criminalística", temas)
        self.assertIsNone(g.category("Un estudio de ADN sobre algas y hámster", "CRIME SCENE"))

    def test_literatura_en_ingles_sin_resenas_rutinarias(self):
        self.assertTrue(g.es_noticia_negrocriminal("The Dagger Awards 2026 shortlist announced"))
        self.assertTrue(g.es_noticia_negrocriminal("New crime novel by a celebrated author"))
        self.assertFalse(g.es_noticia_negrocriminal("Review: a mystery novel from last year"))
        self.assertFalse(g.es_noticia_negrocriminal("Ten books to read this winter"))

    def test_pais_de_suceso_no_del_periodico(self):
        self.assertEqual(g.pais_del_hecho("Detienen a tres personas en Londres"), "REINO UNIDO")
        self.assertEqual(g.pais_del_hecho("La policía investiga un fraude en México"), "MÉXICO")
        self.assertIsNone(g.pais_del_hecho("Operación policial entre China y Rusia"))
        self.assertIsNone(g.pais_del_hecho("Investigan un delito", {"pais_fuente": "RUSIA"}))
        self.assertEqual(g.pais_del_hecho("Investigan una estafa", {"pais_fuente": "ESTADOS UNIDOS", "ambito_nacional": True}), "ESTADOS UNIDOS")

    def test_fuentes_validas(self):
        cfg = json.loads((Path(__file__).resolve().parents[1] / "config/fuentes.json").read_text(encoding="utf-8"))
        self.assertEqual(len({x["url"] for x in cfg}), len(cfg))
        self.assertTrue(all(x.get("idioma") in ("es", "en") for x in cfg if x.get("activo")))
        self.assertFalse(any(x.get("tipo_fuente") == "editorial" and x.get("activo") for x in cfg))
        self.assertTrue(any(x["nombre"].startswith("NIST") and x.get("tematica_verificada") for x in cfg))
        self.assertTrue(any(x["nombre"].startswith("FTC") and x.get("solo_timos") for x in cfg))

    def test_exclusiones_persistentes(self):
        cfg=json.loads((Path(__file__).resolve().parents[1]/"config/noticias_excluidas.json").read_text(encoding="utf-8"))
        ids={x["id"] for x in cfg["noticias"]}
        self.assertIn("cd85adcfa73e12b2", ids)
        self.assertIn("e41f91d600397179", ids)


if __name__ == "__main__":
    unittest.main()
