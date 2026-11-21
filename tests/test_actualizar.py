import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import actualizar as g


class TestGaceta(unittest.TestCase):
    def test_traduccion_sin_alucinaciones(self):
        from traducir import validar, es_ingles, titulo_para_publicar
        self.assertTrue(es_ingles("The Guardian — World", "en"))
        self.assertFalse(es_ingles("La Vanguardia — Barcelona", "es"))
        self.assertFalse(validar(
            "Man accused of murdering his wife in Boston",
            "Condenado por asesinar a su mujer en Boston"))
        self.assertFalse(validar(
            "Police find 316 packages of cocaine",
            "La policía encuentra varios paquetes de cocaína"))
        self.assertTrue(validar(
            "Man accused of stabbing his wife in Boston",
            "Un hombre acusado de apuñalar a su esposa en Boston"))

    def test_traduccion_calidad_y_no_publicar_ingles(self):
        from traducir import validar
        self.assertFalse(validar(
            "Louisiana man charged with killing woman",
            "Louisiana hombre acusado de matar a mujer"))
        self.assertFalse(validar(
            "Teenager learns his fate after fatal joyride",
            "Adolescente aprende su destino tras accidente mortal"))
        self.assertFalse(validar(
            "Alleged cartel boss arrested in raid",
            "Alleged jefe de cartel detenido"))
        from datetime import datetime, timezone
        from email.utils import format_datetime
        from unittest.mock import patch
        feed = {"nombre":"The Guardian — World","idioma":"en","categoria":"AUTO","region":"MUNDO"}
        item = {"title":"Man charged with murder in Bradford",
                "url":"https://example.com/b","date":format_datetime(datetime.now(timezone.utc)),
                "summary":"","outlet":""}
        with patch.object(g, "titulo_para_publicar", return_value=(item["title"],"original")):
            self.assertIsNone(g.make_story(item,feed,[]))
        with patch.object(g, "titulo_para_publicar", return_value=(item["title"],"original")):
            sid = __import__("hashlib").sha1((g.normalize(item["title"])+"|"+
                  datetime.now(timezone.utc).strftime("%Y-%m-%d")).encode()).hexdigest()[:16]
            self.assertEqual(g.make_story(item,feed,[],{sid:"Acusan a un hombre de asesinato en Bradford"})["metodo_titular"],"revision_editorial")

    def test_dedupe_mismo_id_distinta_region(self):
        date = "2026-11-21T18:00:00+00:00"
        def item(region, url):
            return {"id":"test-id","categoria":"TRUE CRIME","region":region,"fecha":date,
                    "actualizado":date,"titular":"Prueba","titular_original":"Prueba",
                    "temas":[],"expedientes":[],"fuentes":[{"url":url,"fecha":date}]}
        noticias = [item("MUNDO","https://a.test/a")]
        self.assertFalse(g.merge_into(noticias,item("EUROPA","https://b.test/b")))
        self.assertEqual(len(noticias),1)
        self.assertEqual(len(noticias[0]["fuentes"]),2)
        self.assertEqual(noticias[0]["region"],"EUROPA")

    def test_titulares_especificos(self):
        from titulares import reescribir_titular
        cases = [
            ("Detenido un hombre por presuntamente matar a su madre en Llívia este lunes",
             ("Llívia", "madre", "presunta")),
            ("Un hombre asesina a su pareja en Parla y se entrega a la policía",
             ("Parla", "pareja", "policía")),
            ("Detenidos dos pasajeros en el aeropuerto de El Prat con 316 bolas de cocaína en su cuerpo",
             ("El Prat", "316", "cocaína")),
            ("Man convicted of starting Palisades fire in Los Angeles",
             ("Palisades", "Los Ángeles", "Condenado")),
            ("French police officers sentenced for beating of music producer Michel Zecler",
             ("Michel Zecler", "Condenados", "policías")),
            ("Teenager allegedly organised arsons and kidnapping on Signal during Melbourne hospitality wars",
             ("Melbourne", "habría", "Signal")),
        ]
        for original, requirements in cases:
            with self.subTest(original=original):
                title, method = reescribir_titular(original)
                self.assertEqual(method, "regla")
                self.assertNotEqual(title, original)
                for fact in requirements:
                    self.assertIn(fact, title)

    def test_no_inventar(self):
        from titulares import reescribir_titular
        original = "Detenido un sospechoso en Barcelona"
        new, method = reescribir_titular(original)
        self.assertEqual(new, original)
        self.assertEqual(method, "original")
        # Sin fecha, lugar o parentesco no se puede inventar un apuñalamiento en Vic.
        original2 = "Un hombre detenido tras un incidente"
        self.assertEqual(reescribir_titular(original2)[0], original2)

    def test_deduplicacion_segun_original(self):
        d = "2026-11-21T08:00:00+00:00"
        def s(title, orig, url):
            return {"categoria":"TRUE CRIME","region":"ESPAÑA","fecha":d,
                    "titular":title, "titular_original":orig,
                    "fuentes":[{"url":url,"fecha":d}]}
        a = s("Vic: detenido un hombre por un presunto delito",
              "Detenido un hombre por el presunto apuñalamiento de su esposa en Vic", "https://a.es/1")
        b = s("Detención por apuñalamiento de una mujer en Vic",
              "Detenido en Vic un hombre por el presunto apuñalamiento de su esposa", "https://b.es/1")
        self.assertTrue(g.same_event(a,b))

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

    def test_no_fuentes_catalanas(self):
        import json
        from pathlib import Path
        feeds = json.loads((Path(__file__).resolve().parents[1] / "config" / "fuentes.json").read_text(encoding="utf-8"))
        self.assertFalse(any(x.get("idioma") == "ca" for x in feeds))
        self.assertFalse(any(x.get("nombre") in g.FUENTES_EXCLUIDAS for x in feeds))

    def test_region_espanola(self):
        self.assertEqual(g.region_of("Detención en Vic"), "ESPAÑA")
        self.assertEqual(g.region_of("Un asesinato en Badalona"), "ESPAÑA")

    def test_regions(self):
        self.assertEqual(g.region_of("Un homicidio en Barcelona", "ESPAÑA"), "ESPAÑA")
        self.assertEqual(g.region_of("Murder trial in Massachusetts", "MUNDO"), "ESTADOS UNIDOS")
        self.assertEqual(g.region_of("Crime in London", "MUNDO"), "EUROPA")
        self.assertEqual(g.region_of("A murder case without a location", "MUNDO"), "MUNDO")

    def test_categoria_ficcion_negrocriminal(self):
        self.assertEqual(g.category("Nueva novela negra premiada en un festival", "AUTO"), "FICCIÓN NEGROCRIMINAL")
        self.assertEqual(g.category("Se estrena un ciclo de cine negro", "AUTO"), "FICCIÓN NEGROCRIMINAL")
        self.assertIn("Ficción negrocriminal", g.topics_of("Nueva novela negra", "FICCIÓN NEGROCRIMINAL"))

    def test_multilingual_categories(self):
        self.assertEqual(g.category("Police arrest suspect in double murder in Texas", "AUTO"), "TRUE CRIME")
        self.assertEqual(g.category("Noves tècniques de digital forensics", "AUTO"), "CRIME SCENE")
        self.assertEqual(g.category("La ministra anuncia una rebaja de impuestos", "AUTO"), None)

    def test_fuente_tematica_no_mete_noticias_ajenas(self):
        from datetime import datetime, timezone
        from email.utils import format_datetime
        now = format_datetime(datetime.now(timezone.utc))
        cfg = [{"id":"extremismo-nihilista-violento", "tipo":"tematico","detector":"nve"}]
        feed = {"nombre":"DOJ", "categoria":"AUTO","idioma":"es",
                "region":"ESTADOS UNIDOS","solo_expediente":"extremismo-nihilista-violento"}
        other = {"title":"Enjuician un robo de coches en Nueva York",
                 "url":"https://example.com/other","date":now,"summary":"","outlet":""}
        linked = {"title":"Detenido un miembro violento de la red 764",
                  "url":"https://example.com/nve","date":now,"summary":"El extremismo nihilista violento","outlet":""}
        self.assertIsNone(g.make_story(other, feed, cfg))
        made = g.make_story(linked, feed, cfg)
        self.assertEqual(made["expedientes"],["extremismo-nihilista-violento"])
        self.assertIn("Extremismo nihilista violento", made["temas"])

    def test_expediente_tematico_nihilista(self):
        from temas_expedientes import coincide
        self.assertTrue(coincide("El FBI alerta del extremismo violento nihilista"))
        self.assertTrue(coincide("Detenido un miembro de la red 764"))
        self.assertTrue(coincide("Com Network linked to nihilistic violent extremism"))
        self.assertTrue(coincide("The Com amenaza a menores", "red criminal nihilista"))
        self.assertFalse(coincide("El nihilismo en la literatura del siglo XIX"))
        self.assertFalse(coincide("Terrorismo yihadista: últimas noticias"))
        self.assertFalse(coincide("Una carretera registra 764 vehículos"))
        self.assertFalse(coincide("Informe sobre el grupo 764 de peces", "ecología submarina"))

        cases = [{"id":"extremismo-nihilista-violento","tipo":"tematico","detector":"nve","alias":["764"]},
                 {"id":"luigi-mangione","alias":["luigi mangione"]}]
        self.assertEqual(g.cases_of("La fiscalía investiga a un miembro de la red 764", cases), ["extremismo-nihilista-violento"])
        self.assertEqual(g.cases_of("La biografía de Luigi Mangione", cases), ["luigi-mangione"])
        self.assertEqual(g.cases_of("Un filósofo escribe sobre nihilismo", cases), [])

    def test_cases(self):
        self.assertEqual(g.cases_of("Novedades en el caso de Lindsay Clancy", [{"id": "lindsay-clancy", "alias": ["Lindsay Clancy"]}]), ["lindsay-clancy"])
        self.assertEqual(g.cases_of("Novedades de Lindsay Johnson", [{"id": "lindsay-clancy", "alias": ["Lindsay Clancy"]}]), [])


if __name__ == "__main__":
    unittest.main()
