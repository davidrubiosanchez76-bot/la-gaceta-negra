#!/usr/bin/env python3
"""La Gaceta Negra: agrega titulares RSS sin reescribir noticias.

Sin dependencias externas. La agrupación de acontecimientos es heurística y conservadora:
combina URLs iguales y titulares muy parecidos en ventanas de 72 horas.
Los títulos originales se conservan internamente para no distorsionar filtros y duplicados.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from pathlib import Path
from titulares import reescribir_titular
from traducir import titulo_para_publicar, es_ingles
from temas_expedientes import coincide as es_extremismo_nihilista

ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc
NOW = datetime.now(UTC)
HEADER = {"User-Agent": "LaGacetaNegra/0.1 (+BalasyEstrellas RSS reader)"}
LIMIT_BYTES = 3_000_000
DAYS_KEEP_FRONTPAGE = 60
DAYS_ACCEPT_FEED = 15

STOP = set("a al ante bajo con contra de del desde durante e el en entre es esta este estos estas la las le les lo los o para por que se sin sobre su sus un una uno unos unas y ya hoy ayer tras nuevo nueva nuevos nuevas caso crimen investigacion investigan detenido detenida presunto presunta ultima ultimas noticia noticias".split())
TOPICS = {
    "Narcotráfico": ("narcotrafico", "narcotrafic", "cocaina", "heroina", "fentanilo", "cartel", "trafico de drogas", "estupefaciente", "droga incautada"),
    "Crimen organizado": ("crimen organizado", "mafia", "organizacion criminal", "banda criminal", "sicario", "trata de personas"),
    "Violencia en la pareja": ("violencia machista", "violencia de genero", "pareja", "expareja", "feminicidio"),
    "Desapariciones": ("desaparecid", "desaparicion", "paradero desconocido", "persona desaparecida"),
    "Criminalística": ("adn", "forense", "criminalistic", "huella dactilar", "medicina legal", "genetica forense", "balistica", "antropologia forense"),
    "Ficción negrocriminal": ("novela negra", "novela policiaca", "literatura negra", "thriller", "premio edgar", "detective literario"),
    "Juicios": ("tribunal", "juicio", "sentencia", "juzgado", "acusacion", "veredicto", "condenad"),
}
CRIME_SCENE = ("adn", "ciencia forense", "tecnica forense", "medicina forense", "criminalistica", "antropologia forense", "balistica", "huellas dactilares", "genetica forense", "identificacion genetica", "restos humanos", "prueba pericial", "forensic", "dna evidence", "forensic dna", "forensic science", "fingerprint analysis", "forensic genealogy", "digital forensics", "crime scene analysis", "evidence testing", "forensic investigation", "forensic technology", "pericia forense", "pericial informatica")
LITERARY = ("novela negra", "novela policiaca", "literatura criminal", "literatura negra", "ficcion criminal", "thriller policiac", "premio edgar", "premio hammett", "festival de novela negra", "novela de misterio", "novela policial", "cine negro", "ficcion noir", "crime fiction", "noir fiction", "mystery novel", "thriller novel", "detective novel", "crime novel", "mystery fiction", "novela negra", "novel·la negra", "novel·la policíaca")
CRIME = ("asesinat", "asesino", "asesina", "homicid", "crimen", "criminal", "detenid", "detien", "blanqueo", "ciberataque", "desaparec", "desaparicion", "secuestro", "narcotraf", "violencia machista", "violencia de genero", "feminicidio", "robo con violencia", "atraco", "sicario", "estafa millonaria", "policia investiga", "presunto asesino", "procesad", "condena por", "asesino en serie", "terrorismo", "trata de personas", "murder", "homicide", "killed", "killing", "slain", "stabbed", "stabbing", "arrested", "rape", "rapist", "sexual assault", "kidnapped", "kidnapping", "fraud", "shooting", "shot dead", "found dead", "missing girl", "missing woman", "missing person", "convicted", "sentenced to prison", "sentenced for", "pleads guilty", "pleaded guilty", "charged with murder", "criminal trial", "death penalty", "crime scene", "assassinat", "assassinat", "homicidi", "detingut", "detinguda", "detenen", "segrest", "narcotrafic", "violencia masclista", "feminicidi", "crim organitzat", "assassi", "desaparicio", "robatori violent", "arson", "murdered", "throat slit")
EXCLUDE = ("accidente de trafico", "colision entre", "incendio forestal", "terremoto", "atropello accidental", "fenomeno meteorologico", "gta vi", "video game", "glider crash", "crashes into", "road accident", "car crash", "plane crash", "forensic focus digest", "registration opens for", "virtual summit", "climate summit")
FUENTES_EXCLUIDAS = {"3CatInfo", "La Vanguardia — Barcelona"}


def read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if not path.exists() or path.read_text(encoding="utf-8") != body:
        path.write_text(body, encoding="utf-8")


def normalize(s):
    s = unicodedata.normalize("NFKD", html.unescape(re.sub(r"<[^>]*>", " ", s or "")))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", s).strip()


def tokens(s):
    return set(t for t in re.findall(r"[a-z0-9]{3,}", normalize(s)) if t not in STOP)


def clean_url(url):
    url = html.unescape((url or "").strip())
    u = urllib.parse.urlsplit(url)
    if u.hostname in {"www.google.com", "google.com"} and u.path == "/url":
        qs = urllib.parse.parse_qs(u.query)
        url = (qs.get("url") or qs.get("q") or [url])[0]
        u = urllib.parse.urlsplit(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        return ""
    tracking = ("utm_", "fbclid", "gclid", "mc_cid", "mc_eid", "ref", "output")
    query = urllib.parse.urlencode([(k, v) for k, v in urllib.parse.parse_qsl(u.query) if not k.lower().startswith(tracking)], doseq=True)
    return urllib.parse.urlunsplit((u.scheme, u.netloc.lower(), u.path.rstrip("/") or "/", query, ""))


def date_parse(raw):
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
    except (ValueError, TypeError, IndexError):
        try:
            dt = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def child_text(elem, local_name):
    for child in elem:
        if child.tag.split("}")[-1] == local_name:
            return "".join(child.itertext()).strip()
    return ""


def rss_items(raw):
    root = ET.fromstring(raw)
    found = []
    for item in root.iter():
        if item.tag.split("}")[-1] not in ("item", "entry"):
            continue
        title = child_text(item, "title")
        url = child_text(item, "link")
        if not url:
            for link in item:
                if link.tag.split("}")[-1] == "link" and link.get("rel", "alternate") in ("alternate", ""):
                    url = link.get("href", "")
                    if url:
                        break
        date = child_text(item, "pubDate") or child_text(item, "published") or child_text(item, "updated") or child_text(item, "date")
        summary = child_text(item, "description") or child_text(item, "summary")
        outlet = child_text(item, "source")
        found.append({"title": title, "url": url, "date": date, "summary": summary, "outlet": outlet})
    return found


def category(text, src):
    s = normalize(text)
    if any(w in s for w in EXCLUDE):
        return None
    if src in ("FICCIÓN NEGROCRIMINAL", "CRIME SCENE"):
        return src
    if any(w in s for w in CRIME_SCENE):
        return "CRIME SCENE"
    if any(w in s for w in LITERARY):
        return "FICCIÓN NEGROCRIMINAL"
    if any(w in s for w in CRIME):
        return "TRUE CRIME"
    return None


def topics_of(text, cat):
    s = normalize(text)
    found = [key for key, words in TOPICS.items() if any(w in s for w in words)]
    if cat == "FICCIÓN NEGROCRIMINAL" and "Ficción negrocriminal" not in found:
        found.append("Ficción negrocriminal")
    if cat == "CRIME SCENE" and "Criminalística" not in found:
        found.append("Criminalística")
    return found


def cases_of(text, config, summary=""):
    s = " " + normalize(text) + " "
    results = []
    for item in config:
        if item.get("activo") is False:
            continue
        if item.get("tipo") == "tematico":
            if item.get("detector") == "nve" and es_extremismo_nihilista(text, summary):
                results.append(item["id"])
        elif any(" " + normalize(alias) + " " in s for alias in item.get("alias", [])):
            results.append(item["id"])
    return results


def location_marker(title):
    # Salvaguarda básica contra operaciones parecidas en lugares diferentes.
    # No pretende ser un reconocedor geográfico completo.
    match = re.search(r"\ben\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñü-]{3,})", title)
    return normalize(match.group(1)) if match else ""


def same_event(a, b):
    # Mismo acontecimiento solo si hay indicios fuertes y fecha próxima.
    if a["categoria"] != b["categoria"]:
        return False
    regions = {story_region(a), story_region(b)}
    if len(regions) > 1:
        return False
    for x in a["fuentes"]:
        if any(x["url"] == y["url"] for y in b["fuentes"]):
            return True
    if abs((date_parse(a["fecha"]) - date_parse(b["fecha"])).total_seconds()) > 72 * 3600:
        return False
    title_a, title_b = a.get("titular_original", a["titular"]), b.get("titular_original", b["titular"])
    loc_a, loc_b = location_marker(title_a), location_marker(title_b)
    if loc_a and loc_b and loc_a != loc_b:
        return False
    left, right = tokens(title_a), tokens(title_b)
    if min(len(left), len(right)) < 4:
        return False
    common = len(left & right)
    jaccard = common / len(left | right)
    coverage = common / min(len(left), len(right))
    text_sim = SequenceMatcher(None, normalize(title_a), normalize(title_b)).ratio()
    return common >= 4 and (jaccard >= .68 or (coverage >= .80 and text_sim >= .66))



# Ámbito del SUCESO, no país de la redacción. La falta de datos se refleja
# como MUNDO, salvo RSS específicamente regionales/nacionales.
GEOGRAFIA = [
    ("ESTADOS UNIDOS", ("estados unidos", "eeuu", "ee.uu", "united states", "usa", "u.s.", "california", "texas", "florida", "massachusetts", "connecticut", "new york", "nueva york", "washington dc", "los angeles", "chicago", "boston", "arizona", "kentucky", "idaho", "ohio", "minnesota", "tennessee", "georgia usa", "new jersey", "pennsylvania")),
    ("ESPAÑA", ("espana", "spain", "madrid", "valencia", "sevilla", "seville", "andalucia", "galicia", "murcia", "bilbao", "zaragoza", "malaga", "alicante", "canarias", "burgos", "castilla", "granada", "asturias", "navarra", "cadiz", "baleares", "pamplona", "vitoria", "policia nacional", "guardia civil", "barcelona", "badalona", "terrassa", "sabadell", "hospitalet", "girona", "gerona", "lleida", "lerida", "tarragona", "mataro", "granollers", "manresa", "catalunya", "cataluna", "catalonia", "mossos", "baix llobregat", "maresme", "barcelones", "valles", "llivia", "vic", "figueres", "puigcerda", "olot", "blanes", "reus", "sitges", "eivissa", "ibiza", "mallorca", "parla", "guadalajara")),
    ("EUROPA", ("reino unido", "united kingdom", "britain", "british", "england", "scotland", "london", "france", "francia", "french", "paris", "italia", "italy", "rome", "roma", "germany", "alemania", "berlin", "polonia", "poland", "portugal", "lisbon", "lisboa", "bruselas", "brussels", "belgica", "belgium", "ukraine", "ucrania", "russia", "rusia", "suiza", "switzerland", "netherlands", "paises bajos", "noruega", "norway", "denmark", "sweden", "suecia", "dinamarca", "ireland", "irlanda", "austria", "grecia", "greece", "hungria", "hungary", "prague", "praga")),
]


def region_of(text, fallback="MUNDO"):
    text = " " + normalize(text) + " "
    for label, names in GEOGRAFIA:
        if any(re.search(r"(?<![a-z])" + re.escape(n) + r"(?![a-z])", text) for n in names):
            return label
    return "ESPAÑA" if fallback == "CATALUÑA" else (fallback if fallback in ("ESPAÑA", "EUROPA", "ESTADOS UNIDOS", "MUNDO") else "MUNDO")


def story_region(story):
    return story.get("region", "MUNDO")


def make_story(item, feed, config, correcciones=None):
    title = html.unescape(re.sub(r"<[^>]+>", "", item["title"])).strip()
    url = clean_url(item["url"])
    date = date_parse(item["date"])
    if not title or not url or not date:
        return None
    if not (NOW - timedelta(days=DAYS_ACCEPT_FEED) <= date <= NOW + timedelta(hours=8)):
        return None
    full_text = title + " " + re.sub(r"<[^>]*>", " ", item["summary"])
    es_nve = es_extremismo_nihilista(title, item["summary"])
    # Los RSS especializados en seguimiento no deben inundar la portada.
    if feed.get("solo_expediente") and feed["solo_expediente"] not in cases_of(title, config, summary=item["summary"]):
        return None
    cat = category(title, feed.get("categoria", "AUTO"))
    if not cat and es_nve:
        cat = "TRUE CRIME"
    if not cat:
        return None
    dt = date.isoformat(timespec="seconds")
    idioma = 'en' if es_ingles(feed['nombre'], feed.get('idioma','')) else 'es'
    editorial, metodo = titulo_para_publicar(title, cat, idioma)
    sid = hashlib.sha1((normalize(title) + "|" + date.strftime("%Y-%m-%d")).encode()).hexdigest()[:16]
    if sid in (correcciones or {}):
        editorial, metodo = correcciones[sid], "revision_editorial"
    if idioma == "en" and metodo == "original":
        # No incorporar titulares en inglés sin una traducción revisable al español.
        print(f"TRADUCCION PENDIENTE: {title[:130]}", file=sys.stderr)
        return None
    return {
        "id": sid,
        "titular": editorial[:260], "titular_original": title[:260], "metodo_titular": metodo, "fecha": dt, "actualizado": dt,
        "categoria": cat, "region": region_of(title, feed.get("region", "MUNDO")),
        "temas": sorted(set(topics_of(title, cat) + (["Extremismo nihilista violento"] if es_nve else []))),
        "expedientes": cases_of(title, config, summary=item["summary"]),
        "etiquetas_de_deteccion": ["nve"] if es_nve else [],
        "fuentes": [{"medio": item.get("outlet") or (urllib.parse.urlsplit(url).hostname.removeprefix("www.") if "Google Alerts" in feed["nombre"] else feed["nombre"]), "url": url, "fecha": dt}],
    }


def merge_into(stories, new):
    for old in stories:
        if old.get("id") == new.get("id") or same_event(old, new):
            urls = {x["url"] for x in old["fuentes"]}
            for source in new["fuentes"]:
                if source["url"] not in urls:
                    old["fuentes"].append(source)
            old["temas"] = sorted(set(old["temas"]) | set(new["temas"]))
            old["expedientes"] = sorted(set(old["expedientes"]) | set(new["expedientes"]))
            old["actualizado"] = max(old["actualizado"], new["actualizado"])
            if old.get("region") == "MUNDO" and new.get("region") not in ("MUNDO", None):
                old["region"] = new["region"]
            # Conservar primer titular escogido (URL estable) y fuentes por orden de llegada.
            return False
    stories.append(new)
    return True


def fetch(url):
    req = urllib.request.Request(url, headers=HEADER)
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = resp.read(LIMIT_BYTES + 1)
        if len(data) > LIMIT_BYTES:
            raise ValueError("RSS demasiado grande")
        return data


def main():
    feeds = read_json(ROOT / "config/fuentes.json", [])
    watch = read_json(ROOT / "config/expedientes.json", [])
    correcciones = read_json(ROOT / "config/titulares_revisados.json", {})
    folder = ROOT / "archivo"
    stories = []
    def review_old(old):
        # Eliminar de portada y archivo todas las fuentes excluidas, también en fichas agrupadas.
        old["fuentes"] = [f for f in old.get("fuentes", []) if f.get("medio") not in FUENTES_EXCLUIDAS]
        if not old["fuentes"]:
            return None
        if old.get("region") == "CATALUÑA":
            old["region"] = "ESPAÑA"
        # Conservar intactos los titulares de hemeroteca seleccionados y verificados.
        # Su fecha, fuente, categoría y texto ya fueron comprobados editorialmente.
        if old.get("origen") == "hemeroteca_manual":
            return old
        # A partir de 0.2, una palabra en el resumen de otro tema no basta.
        # Revalidar incluso las entradas ya publicadas para retirar falsos positivos.
        source = (old.get("fuentes") or [{}])[0].get("medio", "")
        origin = next((f for f in feeds if f["nombre"] == source), {})
        hint = origin.get("categoria", "AUTO")
        if hint == "AUTO" and source.startswith("Revista Calibre"):
            hint = "FICCIÓN NEGROCRIMINAL"
        if hint == "AUTO" and source.startswith("ScienceDaily"):
            hint = "CRIME SCENE"
        original = old.get("titular_original") or old.get("titular", "")
        es_nve = ("nve" in old.get("etiquetas_de_deteccion", [])) or es_extremismo_nihilista(original)
        cat = category(original, hint)
        if not cat and es_nve:
            cat = "TRUE CRIME"
        if not cat:
            return None
        old["categoria"] = cat
        old["titular_original"] = original[:260]
        idioma = "en" if es_ingles(source, origin.get("idioma","")) else "es"
        if old.get("id") in correcciones:
            old["titular"], old["metodo_titular"] = correcciones[old["id"]], "revision_editorial"
        else:
            candidato, metodo = titulo_para_publicar(original, cat, idioma)
            # Si falla temporalmente el motor, no destruir una traducción previa válida.
            if not (idioma == "en" and metodo == "original"
                    and old.get("metodo_titular") in ("traduccion_automatica", "regla", "revision_editorial")
                    and old.get("titular") and old["titular"] != original):
                old["titular"], old["metodo_titular"] = candidato, metodo
        old["region"] = region_of(original, origin.get("region", "MUNDO"))
        old["temas"] = sorted(set(topics_of(original, cat) + (["Extremismo nihilista violento"] if es_nve else [])))
        old["expedientes"] = sorted(set(cases_of(original, watch) + (["extremismo-nihilista-violento"] if es_nve and any(c.get("id") == "extremismo-nihilista-violento" and c.get("activo", True) for c in watch) else [])))
        old["etiquetas_de_deteccion"] = ["nve"] if es_nve else []
        return old

    for month_file in sorted(folder.glob("????-??.json")):
        for raw in read_json(month_file, {}).get("noticias", []):
            old = review_old(raw)
            if old:
                stories.append(old)
    # Compatible con una instalación nueva que aún no tenga archivos históricos.
    for raw in read_json(ROOT / "data/noticias.json", {}).get("noticias", []):
        old = review_old(raw)
        if old and not any(x["id"] == old["id"] for x in stories):
            stories.append(old)
    # Dos RSS pueden contener exactamente la misma noticia pero regiones distintas;
    # unificar por ID antes de recopilar, sin borrar sus fuentes ni su hemeroteca.
    unicas, por_id = [], {}
    for noticia in stories:
        anterior = por_id.get(noticia["id"])
        if anterior is None:
            por_id[noticia["id"]] = noticia
            unicas.append(noticia)
        else:
            urls = {f["url"] for f in anterior.get("fuentes", [])}
            for fuente in noticia.get("fuentes", []):
                if fuente["url"] not in urls:
                    anterior["fuentes"].append(fuente)
                    urls.add(fuente["url"])
            anterior["temas"] = sorted(set(anterior.get("temas", [])) | set(noticia.get("temas", [])))
            anterior["expedientes"] = sorted(set(anterior.get("expedientes", [])) | set(noticia.get("expedientes", [])))
            anterior["actualizado"] = max(anterior.get("actualizado", anterior["fecha"]), noticia.get("actualizado", noticia["fecha"]))
            if anterior.get("region") == "MUNDO" and noticia.get("region") not in ("MUNDO", None):
                anterior["region"] = noticia["region"]
    stories = unicas
    success = found = new_count = 0
    for f in feeds:
        if not f.get("activo", True):
            continue
        try:
            items = rss_items(fetch(f["url"]))
            success += 1
            count = 0
            for article in items:
                story = make_story(article, f, watch, correcciones)
                if story:
                    found += 1
                    if merge_into(stories, story):
                        new_count += 1
                    count += 1
            print(f"OK {f['nombre']}: {len(items)} entradas, {count} pertinentes")
        except Exception as exc:
            print(f"AVISO {f['nombre']}: {type(exc).__name__}: {exc}", file=sys.stderr)
    if success == 0:
        print("ERROR: ninguna fuente respondió. Se mantienen intactos los JSON.", file=sys.stderr)
        sys.exit(1)
    stories.sort(key=lambda s: (s["fecha"], s["id"]), reverse=True)
    cutoff = NOW - timedelta(days=DAYS_KEEP_FRONTPAGE)
    current = [x for x in stories if date_parse(x["fecha"]) >= cutoff]
    now_str = NOW.isoformat(timespec="seconds")
    current_doc = {"actualizado": now_str, "total": len(current), "noticias": current}
    # Evitar commits inútiles cuando no aparecen noticias nuevas.
    previous = read_json(ROOT / "data/noticias.json", {})
    if previous.get("noticias", []) != current or previous.get("total") != len(current):
        write_json(ROOT / "data/noticias.json", current_doc)
    months = {}
    for story in stories:
        month = story["fecha"][:7]
        months.setdefault(month, []).append(story)
    manifest = []
    for month, items in sorted(months.items(), reverse=True):
        path = folder / (month + ".json")
        month_doc = {"mes": month, "total": len(items), "noticias": items}
        if read_json(path, None) != month_doc:
            write_json(path, month_doc)
        manifest.append({"mes": month, "total": len(items), "expedientes": sorted({c for s in items for c in s["expedientes"]}), "temas": sorted({t for s in items for t in s["temas"]}), "regiones": sorted({story_region(s) for s in items})})
    manifest_doc = {"meses": manifest}
    if read_json(folder / "indice.json", None) != manifest_doc:
        write_json(folder / "indice.json", manifest_doc)
    print(f"FINAL: {success} RSS accesibles; {found} artículos pertinentes; {new_count} nuevas fichas; {len(stories)} noticias archivadas")


if __name__ == "__main__":
    main()
