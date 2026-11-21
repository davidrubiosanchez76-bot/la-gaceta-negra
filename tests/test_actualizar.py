import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import actualizar as g


class TestGaceta(unittest.TestCase):
    def test_feed(self):
        xml = b'<rss><channel><item><title>Detenido el autor de un crimen</title><link>https://medio.es/noticia?utm_source=rss</link><pubDate>Fri, 20 Nov 2026 12:00:00 GMT</pubDate></item></channel></rss>'
        i = g.rss_items(xml)[0]
        self.assertIn("crimen", i["title"])
        self.assertEqual(g.clean_url(i["url"]), "https://medio.es/noticia")

    def test_conservador(self):
        d = "2026-11-21T08:00:00+00:00"
        def s(title, url):
            return {"categoria": "TRUE CRIME", "fecha": d, "titular": title, "fuentes": [{"medio": "Medio", "url": url, "fecha": d}], "temas": [], "expedientes": [], "actualizado": d}
        a = s("Desarticulada una red de narcotráfico en Valencia con veinte detenidos", "https://a.es/1")
        b = s("La policía desarticula una red de narcotráfico en Valencia: veinte detenidos", "https://b.es/1")
        c = s("Desarticulada una red de narcotráfico en Sevilla con veinte detenidos", "https://c.es/1")
        self.assertTrue(g.same_event(a, b))
        self.assertFalse(g.same_event(a, c))

    def test_regions(self):
        self.assertEqual(g.region_of("Un homicidio en Barcelona", "ESPAÑA"), "CATALUÑA")
        self.assertEqual(g.region_of("Murder trial in Massachusetts", "MUNDO"), "ESTADOS UNIDOS")
        self.assertEqual(g.region_of("Crime in London", "MUNDO"), "EUROPA")
        self.assertEqual(g.region_of("A murder case without a location", "MUNDO"), "MUNDO")

    def test_multilingual_categories(self):
        self.assertEqual(g.category("Police arrest suspect in double murder in Texas", "AUTO"), "TRUE CRIME")
        self.assertEqual(g.category("Noves tècniques de digital forensics", "AUTO"), "CRIME SCENE")
        self.assertEqual(g.category("La ministra anuncia una rebaja de impuestos", "AUTO"), None)

    def test_cases(self):
        self.assertEqual(g.cases_of("Novedades en el caso de Lindsay Clancy", [{"id": "lindsay-clancy", "alias": ["Lindsay Clancy"]}]), ["lindsay-clancy"])
        self.assertEqual(g.cases_of("Novedades de Lindsay Johnson", [{"id": "lindsay-clancy", "alias": ["Lindsay Clancy"]}]), [])


if __name__ == "__main__":
    unittest.main()
