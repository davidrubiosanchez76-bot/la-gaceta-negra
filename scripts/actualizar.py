#!/usr/bin/env python3
"""La Gaceta Negra: agrega titulares RSS sin reescribir noticias.

Sin dependencias externas. La agrupación de acontecimientos es heurística y conservadora:
combina URLs iguales y titulares muy parecidos en ventanas de 72 horas.
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
    "Literatura negra": ("novela negra", "novela policiaca", "literatura negra", "thriller", "premio edgar", "detective literario"),
    "Juicios": ("tribunal", "juicio", "sentencia", "juzgado", "acusacion", "veredicto", "condenad"),
}
CRIME_SCENE = ("adn", "ciencia forense", "tecnica forense", "medicina forense", "criminalistica", "antropologia forense", "balistica", "huellas dactilares", "genetica forense", "identificacion genetica", "restos humanos", "prueba pericial")
LITERARY = ("novela negra", "novela policiaca", "literatura criminal", "literatura negra", "ficcion criminal", "thriller", "escritor", "escritora", "editorial", "premio edgar", "detective literario", "festival de novela negra", "novela de misterio", "libro", "novela")
CRIME = ("asesinat", "homicid", "crimen", "criminal", "detenid", "desaparec", "desaparicion", "secuestro", "narcotraf", "violencia machista", "violencia de genero", "feminicidio", "robo con violencia", "atraco", "sicario", "estafa millonaria", "policia investiga", "presunto asesino", "procesad", "condena por", "asesino en serie", "terrorismo", "trata de personas")
EXCLUDE = ("accidente de trafico", "colision entre", "incendio forestal", "terremoto", "atropello accidental", "fenomeno meteorologico")


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
    if src in ("LITERATURA NEGRA", "CRIME SCENE"):
        return src
    if any(w in s for w in CRIME_SCENE):
        return "CRIME SCENE"
    if any(w in s for w in LITERARY):
        return "LITERATURA NEGRA"
    if any(w in s for w in CRIME):
        return "TRUE CRIME"
    return None


def topics_of(text, cat):
    s = normalize(text)
    found = [key for key, words in TOPICS.items() if any(w in s for w in words)]
    if cat == "LITERATURA NEGRA" and "Literatura negra" not in found:
        found.append("Literatura negra")
    if cat == "CRIME SCENE" and "Criminalística" not in found:
        found.append("Criminalística")
    return found


def cases_of(text, config):
    s = " " + normalize(text) + " "
    return [x["id"] for x in config if x.get("activo", True) and any(" " + normalize(alias) + " " in s for alias in x.get("alias", []))]


def location_marker(title):
    # Salvaguarda básica contra operaciones parecidas en lugares diferentes.
    # No pretende ser un reconocedor geográfico completo.
    match = re.search(r"\ben\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñü-]{3,})", title)
    return normalize(match.group(1)) if match else ""


def same_event(a, b):
    # Mismo acontecimiento solo si hay indicios fuertes y fecha próxima.
    if a["categoria"] != b["categoria"]:
        return False
    for x in a["fuentes"]:
        if any(x["url"] == y["url"] for y in b["fuentes"]):
            return True
    if abs((date_parse(a["fecha"]) - date_parse(b["fecha"])).total_seconds()) > 72 * 3600:
        return False
    loc_a, loc_b = location_marker(a["titular"]), location_marker(b["titular"])
    if loc_a and loc_b and loc_a != loc_b:
        return False
    left, right = tokens(a["titular"]), tokens(b["titular"])
    if min(len(left), len(right)) < 4:
        return False
    common = len(left & right)
    jaccard = common / len(left | right)
    coverage = common / min(len(left), len(right))
    text_sim = SequenceMatcher(None, normalize(a["titular"]), normalize(b["titular"])).ratio()
    return common >= 4 and (jaccard >= .68 or (coverage >= .80 and text_sim >= .66))


def make_story(item, feed, config):
    title = html.unescape(re.sub(r"<[^>]+>", "", item["title"])).strip()
    url = clean_url(item["url"])
    date = date_parse(item["date"])
    if not title or not url or not date:
        return None
    if not (NOW - timedelta(days=DAYS_ACCEPT_FEED) <= date <= NOW + timedelta(hours=8)):
        return None
    full_text = title + " " + re.sub(r"<[^>]*>", " ", item["summary"])
    cat = category(full_text, feed.get("categoria", "AUTO"))
    if not cat:
        return None
    dt = date.isoformat(timespec="seconds")
    return {
        "id": hashlib.sha1((normalize(title) + "|" + date.strftime("%Y-%m-%d")).encode()).hexdigest()[:16],
        "titular": title[:260], "fecha": dt, "actualizado": dt,
        "categoria": cat, "temas": topics_of(full_text, cat),
        "expedientes": cases_of(title, config),
        "fuentes": [{"medio": item.get("outlet") or (urllib.parse.urlsplit(url).hostname.removeprefix("www.") if "Google Alerts" in feed["nombre"] else feed["nombre"]), "url": url, "fecha": dt}],
    }


def merge_into(stories, new):
    for old in stories:
        if same_event(old, new):
            urls = {x["url"] for x in old["fuentes"]}
            for source in new["fuentes"]:
                if source["url"] not in urls:
                    old["fuentes"].append(source)
            old["temas"] = sorted(set(old["temas"]) | set(new["temas"]))
            old["expedientes"] = sorted(set(old["expedientes"]) | set(new["expedientes"]))
            old["actualizado"] = max(old["actualizado"], new["actualizado"])
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
    folder = ROOT / "archivo"
    stories = []
    for month_file in sorted(folder.glob("????-??.json")):
        for old in read_json(month_file, {}).get("noticias", []):
            stories.append(old)
    # Compatible con una instalación nueva que aún no tenga archivos históricos.
    for old in read_json(ROOT / "data/noticias.json", {}).get("noticias", []):
        if not any(x["id"] == old["id"] for x in stories):
            stories.append(old)
    success = found = new_count = 0
    for f in feeds:
        if not f.get("activo", True):
            continue
        try:
            items = rss_items(fetch(f["url"]))
            success += 1
            count = 0
            for article in items:
                story = make_story(article, f, watch)
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
        manifest.append({"mes": month, "total": len(items), "expedientes": sorted({c for s in items for c in s["expedientes"]}), "temas": sorted({t for s in items for t in s["temas"]})})
    manifest_doc = {"meses": manifest}
    if read_json(folder / "indice.json", None) != manifest_doc:
        write_json(folder / "indice.json", manifest_doc)
    print(f"FINAL: {success} RSS accesibles; {found} artículos pertinentes; {new_count} nuevas fichas; {len(stories)} noticias archivadas")


if __name__ == "__main__":
    main()
