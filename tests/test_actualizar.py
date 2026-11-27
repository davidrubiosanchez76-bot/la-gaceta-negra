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

    def test_relevancia_noir_estricta(self):
        self.assertIsNone(g.category("¿Por qué desaparecieron los neandertales? Un estudio señala el papel decisivo que tuvo el Homo sapiens", "AUTO"))
        self.assertIsNone(g.category("Un equipo de científicos crea un planimal fusionando ADN de hámster y algas", "AUTO"))
        self.assertIsNone(g.category("Tres muertos y decenas desaparecidos después del incendio en la fábrica de Indonesia", "AUTO"))
        self.assertIsNone(g.category("Jennifer Lawrence lamenta la desaparición del arco de Katniss", "AUTO"))
        self.assertIsNone(g.category("Un genoma de dinosaurio permite nuevos estudios genéticos", "AUTO"))
        self.assertEqual(g.category("Hallan indicios de homicidio prehistórico en Atapuerca", "AUTO"), "TRUE CRIME")
        self.assertEqual(g.category("Una mujer desaparecida es localizada en Girona por la policía", "AUTO"), "TRUE CRIME")
        self.assertEqual(g.category("Investigan la desaparición de una niña en Barcelona", "AUTO"), "TRUE CRIME")
        self.assertEqual(g.category("La prueba de ADN forense permite identificar a un sospechoso", "AUTO"), "CRIME SCENE")
        self.assertEqual(g.category("Nuevas técnicas de análisis forense", "CRIME SCENE"), "CRIME SCENE")
        self.assertIsNone(g.category("Ciencia general sobre hámsteres", "CRIME SCENE"))

    def test_exclusion_editorial_persistente(self):
        import json
        from datetime import datetime, timezone
        from email.utils import format_datetime
        registros=json.loads((Path(__file__).resolve().parents[1] / "config" / "noticias_excluidas.json").read_text(encoding="utf-8"))
        excluidas={x["id"] for x in registros["noticias"]}
        self.assertIn("cbd8150bf898c418", excluidas)
        titulo="¿Por qué desaparecieron los neandertales? Un estudio señala el papel decisivo que tuvo el Homo sapiens"
        noticia={"title":titulo, "url":"https://example.org/neandertales",
                 "date":format_datetime(datetime.now(timezone.utc)),"summary":"","outlet":""}
        self.assertIsNone(g.make_story(noticia,{"nombre":"elDiario.es","categoria":"AUTO","idioma":"es"},[],excluidas=excluidas))

    def test_preferencia_lectura_publica(self):
        import json
        cfg=json.loads((Path(__file__).resolve().parents[1] / "config" / "acceso_medios.json").read_text(encoding="utf-8"))
        pago={"medio":"EL PAÍS — España","url":"https://elpais.com/espana/noticia"}
        libre={"medio":"20minutos","url":"https://www.20minutos.es/noticia/1"}
        neutra={"medio":"Medio sin política","url":"https://example.org/noticia"}
        caso={"fuentes":[pago,neutra,libre]}
        g.ordenar_fuentes(caso,cfg)
        self.assertEqual(caso["fuentes"],[libre,neutra,pago])
        self.assertEqual(g.prioridad_fuente(dict(pago,acceso="abierto"),cfg),0)
        self.assertEqual(g.prioridad_fuente({"medio":"EL PAÍS","url":"https://example.org/test"},cfg),1)
        sola={"fuentes":[pago]}
        g.ordenar_fuentes(sola,cfg)
        self.assertEqual(sola["fuentes"],[pago])
        en={"medio":"The Guardian — World","url":"https://www.theguardian.com/world/test"}
        castellano={"fuentes":[en,libre]}
        g.ordenar_fuentes(castellano,cfg)
        self.assertEqual(castellano["fuentes"][0],libre)

    def test_alternativas_de_mismo_suceso(self):
        import json
        cfg=json.loads((Path(__file__).resolve().parents[1] / "config" / "acceso_medios.json").read_text(encoding="utf-8"))
        fecha="2026-11-22T08:00:00+00:00"
        def caso(medio,url):
            return {"id":"identico","categoria":"TRUE CRIME","region":"ESPAÑA",
                    "fecha":fecha,"actualizado":fecha,"titular":"Un suceso",
                    "titular_original":"Un suceso","medio_titular":medio,
                    "temas":[],"expedientes":[],"fuentes":[{"medio":medio,"url":url,"fecha":fecha}]}
        pago=caso("EL PAÍS — España","https://elpais.com/test")
        libre=caso("Europa Press — España","https://www.europapress.es/test")
        lista=[pago]
        self.assertFalse(g.merge_into(lista,libre))
        g.ordenar_fuentes(lista[0],cfg)
        self.assertEqual(len(lista),1)
        self.assertEqual(lista[0]["fuentes"][0]["medio"],"Europa Press — España")
        self.assertEqual(lista[0]["fuentes"][1]["medio"],"EL PAÍS — España")
        self.assertEqual(lista[0]["medio_titular"],"EL PAÍS — España")

    def test_noticias_blogs_de_novela_negra(self):
        self.assertTrue(g.es_noticia_negrocriminal("Pedro Feijoo gana el premio de novela Cartagena Negra"))
        self.assertTrue(g.es_noticia_negrocriminal("Presentación del festival Getafe Negro"))
        self.assertTrue(g.es_noticia_negrocriminal("Convocatoria del premio Hammett"))
        self.assertTrue(g.es_noticia_negrocriminal("Novedades editoriales de novela negra"))
        self.assertFalse(g.es_noticia_negrocriminal("La ciudad como coartada por Roberto R. Díaz Blanco"))
        self.assertFalse(g.es_noticia_negrocriminal("Reseña de la novela Las huellas"))
        self.assertFalse(g.es_noticia_negrocriminal("Los cinco detectives favoritos del autor"))
        from datetime import datetime, timezone
        from email.utils import format_datetime
        feed = {"nombre":"Solo Novela Negra","categoria":"FICCIÓN NEGROCRIMINAL",
                "idioma":"es","region":"MUNDO","solo_noticias_genero":True}
        def item(title):
            return {"title":title,"url":"https://example.com/post",
                    "date":format_datetime(datetime.now(timezone.utc)),"summary":"","outlet":""}
        self.assertIsNone(g.make_story(item("Reseña: una novela policiaca muy interesante"),feed,[]))
        accepted = g.make_story(item("El festival Getafe Negro presenta su programación"),feed,[])
        self.assertEqual(accepted["categoria"],"FICCIÓN NEGROCRIMINAL")

    def test_fuentes_nuevos_medios_y_blogs(self):
        import json
        feeds=json.loads((Path(__file__).resolve().parents[1] / "config" / "fuentes.json").read_text(encoding="utf-8"))
        index={f["nombre"]:f for f in feeds}
        for name in ("OKDIARIO — España","THE OBJECTIVE — España","El Debate — Portada",
                     "ABC — Última hora","El Confidencial — España","EL MUNDO — España",
                     "Solo Novela Negra","Inmisericordes","Interrobang","Zenda — Novela Negra"):
            self.assertIn(name,index)
            self.assertTrue(index[name]["activo"])
        for name in ("Solo Novela Negra","Inmisericordes","Interrobang","Zenda — Novela Negra"):
            self.assertTrue(index[name]["solo_noticias_genero"])


    def test_filtrar_polemica_sin_criminalizar_politica(self):
        ejemplos_fuera = [
            "La izquierda sale a la ofensiva contra Abascal y Feijóo por los recortes y la violencia machista",
            "Zasca de Abascal a Sánchez por recriminarle que no condene la violencia machista: Usted ha liberado violadores",
            "Colau promete firmeza con Abascal y Feijóo en el debate a cuatro",
            "Feijóo y Ayuso alimentan el fantasma del fraude electoral",
            "El PP utiliza el día contra la violencia machista para cargar contra el Gobierno",
            "Vox sobre los siete empadronados en Marbella: este es el fraude para amañar las elecciones",
            "El PP anuncia sus programas para combatir la violencia machista",
        ]
        for titulo in ejemplos_fuera:
            with self.subTest(titulo=titulo):
                self.assertIsNone(g.category(titulo, "AUTO"))
        ejemplos_dentro = [
            "La policía detiene a un alcalde por fraude en las cuentas municipales",
            "Un banco que financió a Vox prestó servicio a una supuesta red de blanqueo rusa",
            "Dimite un cargo del partido de Erdogan tras implicarse a su hijo en un fraude millonario",
            "El etarra Jon Bienzobas sale en libertad tras cumplir 27 años de prisión",
            "Detenido un hombre por asesinar a su pareja en Murcia",
            "La fiscalía acusa a un diputado de un delito de corrupción",
        ]
        for titulo in ejemplos_dentro:
            with self.subTest(titulo=titulo):
                self.assertEqual(g.category(titulo, "AUTO"), "TRUE CRIME")

    def test_etiquetas_todas_las_categorias(self):
        self.assertIn("Homicidios y asesinatos", g.topics_of("La policía investiga un asesinato en Girona", "TRUE CRIME"))
        self.assertIn("Investigación policial", g.topics_of("La policía investiga un asesinato en Girona", "TRUE CRIME"))
        self.assertIn("Agresiones sexuales", g.topics_of("Detienen a un violador", "TRUE CRIME"))
        self.assertIn("Estafas y fraudes", g.topics_of("Condenado por blanqueo y estafa", "TRUE CRIME"))
        self.assertIn("Ciberdelincuencia", g.topics_of("Un hacker ataca un sistema policial", "TRUE CRIME"))
        self.assertIn("Narcotráfico", g.topics_of("Incautan cocaína a un cártel", "TRUE CRIME"))
        self.assertIn("Festivales", g.topics_of("El festival Getafe Negro presenta su programa", "FICCIÓN NEGROCRIMINAL"))
        self.assertIn("Ficción negrocriminal", g.topics_of("Festival de novela negra", "FICCIÓN NEGROCRIMINAL"))
        self.assertIn("Criminalística", g.topics_of("Nuevas pruebas forenses", "CRIME SCENE"))
        self.assertEqual(g.topics_of("Suceso sin palabras temáticas", "TRUE CRIME"), ["Actualidad criminal"])

    def test_lawcrime_exigir_revision_editorial(self):
        self.assertTrue(g.titular_complejo_lawcrime(
            "Grandmother defending kids from daughter's stalker shot dead after confronting gunman in home: Family and cops"))
        self.assertTrue(g.titular_complejo_lawcrime(
            "Husband who reported wife missing charged with murder after her body was found near abandoned building: Police"))
        self.assertFalse(g.titular_complejo_lawcrime("Woman arrested for murder"))
        import json
        fixes=json.loads((Path(__file__).resolve().parents[1] / "config" / "titulares_revisados.json").read_text(encoding="utf-8"))
        for ident in ("8d3d016f32047414","a4dcb27b4e5ebb66","ff822ce0630c17d3"):
            self.assertIn(ident, fixes)


    def test_no_noticias_de_campana_sobre_violencia_machista(self):
        excluir = (
            "Abascal, sobre la pregunta de Colau acerca de la violencia de género: Me dio un asco infinito",
            "La violencia machista sacude el final de la campaña: 50 asesinadas, la última mientras debatían los candidatos",
            "Ada Colau brilla en el debate y se abre un hueco en la campaña por no quedarse calladita",
            "EH Bildu suspende todos sus actos, incluido el cierre de campaña, como protesta por el asesinato machista en Bilbao",
            "Inda agradece a Sánchez su mención en el debate sobre corrupción",
            "La izquierda sale a la ofensiva contra Abascal y Feijóo por la violencia machista",
            "Isabel Rodríguez pide el voto a las mujeres para defender leyes contra la violencia machista",
            "Feijóo y Ayuso critican a Sánchez en campaña por la violencia de género",
            "Una concejala carga contra el negacionismo de la violencia machista",
        )
        for titulo in excluir:
            with self.subTest(titulo=titulo):
                self.assertIsNone(g.category(titulo, "AUTO"))
        mantener = (
            "Detienen a un diputado del PP por blanqueo de capitales",
            "La fiscalía investiga a un dirigente de Vox por presunta corrupción",
            "Un alcalde socialista condenado por malversación de fondos",
            "La Guardia Civil detiene al sospechoso del asesinato machista en Bilbao durante la campaña",
            "Investigan como violencia machista el asesinato de una mujer en Murcia",
            "Las víctimas mortales por violencia machista suben a 49 al confirmarse dos casos más",
            "Un banco vinculado a un partido prestó servicio a una red de blanqueo rusa",
        )
        for titulo in mantener:
            with self.subTest(titulo=titulo):
                self.assertEqual(g.category(titulo, "AUTO"), "TRUE CRIME")

    def test_limpieza_de_polemicas_en_datos_publicados(self):
        import json
        raiz=Path(__file__).resolve().parents[1]
        vetados={"b6f9bf537844cff1", "a3f05387bb2dd1ea",
                 "0c4537c1d02b32b0", "8d0227379be3efe0"}
        exclusiones=json.loads((raiz/"config"/"noticias_excluidas.json").read_text(encoding="utf-8"))
        self.assertTrue(vetados.issubset({x["id"] for x in exclusiones["noticias"]}))
        for ruta in (raiz/"data"/"noticias.json", raiz/"archivo"/"2026-11.json"):
            publicado=json.loads(ruta.read_text(encoding="utf-8"))
            self.assertFalse(vetados & {x["id"] for x in publicado["noticias"]})

    def test_cases(self):
        self.assertEqual(g.cases_of("Novedades en el caso de Lindsay Clancy", [{"id": "lindsay-clancy", "alias": ["Lindsay Clancy"]}]), ["lindsay-clancy"])
        self.assertEqual(g.cases_of("Novedades de Lindsay Johnson", [{"id": "lindsay-clancy", "alias": ["Lindsay Clancy"]}]), [])


if __name__ == "__main__":
    unittest.main()
