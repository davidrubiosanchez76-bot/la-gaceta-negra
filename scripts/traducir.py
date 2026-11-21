"""Traducción sin API de pago de titulares ingleses al castellano.

Se utiliza Argos Translate (modelo inglés-español) instalado en GitHub Actions.
Si el modelo no está disponible o se pierden hechos importantes, no se inventa:
se conserva el titular original y se registra el motivo.
"""
from __future__ import annotations
import re
import unicodedata
from functools import lru_cache

MEDIOS_INGLES = ("Law & Crime", "NPR", "BBC News", "The Guardian", "CrimeReads", "Forensic Focus", "ScienceDaily")

def es_ingles(medio, idioma=""):
    return idioma == "en" or (not idioma and any(medio.startswith(m) for m in MEDIOS_INGLES))

def sin_acentos(texto):
    t=unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in t if not unicodedata.combining(c))

@lru_cache(maxsize=1)
def motor():
    try:
        from argostranslate import translate
        langs=translate.get_installed_languages()
        en=next((x for x in langs if x.code=="en"),None)
        es=next((x for x in langs if x.code=="es"),None)
        return en.get_translation(es) if en and es else None
    except (ImportError,RuntimeError,ValueError,AttributeError):
        return None

def validar(original, traducido):
    """Rechaza pérdidas evidentes de cifras y modalidades de imputación."""
    if not traducido or traducido.strip().lower()==original.strip().lower():
        return False
    if len(traducido)<14 or len(traducido)>350:
        return False
    old=set(re.findall(r"\b\d+(?:[.,]\d+)?\b",original))
    new=set(re.findall(r"\b\d+(?:[.,]\d+)?\b",traducido))
    if not old.issubset(new):
        return False
    a=sin_acentos(original)
    b=sin_acentos(traducido)
    # Estas palabras obligan a una atribución de la sospecha al traducir.
    if re.search(r"\b(allegedly|alleged|suspect|suspected|accused|charged|reportedly)\b",a):
        if not re.search(r"\b(presunt|supuest|sospech|acusad|imputad|investigad|detenid|alegad|presumib|habria|segun)\w*",b):
            return False
    # Afirmar una condena donde la noticia habla de una acusación cambia el hecho.
    if re.search(r"\b(allegedly|alleged|suspect|suspected|accused|charged)\b",a):
        if re.search(r"\b(condenad|culpable|confeso)\w*",b) and not re.search(r"\b(no|sin|todavia no)\b",b):
            return False
    return True

def traducir(titulo):
    m=motor()
    if not m:
        return None
    try:
        s=re.sub(r"\s+", " ", m.translate(titulo)).strip().rstrip(".")
    except Exception:
        return None
    if not validar(titulo,s):
        return None
    return s[:1].upper()+s[1:] if s else None

def titulo_para_publicar(original, categoria, idioma=""):
    from titulares import reescribir_titular
    editorial, metodo = reescribir_titular(original, categoria)
    if metodo=="regla":
        return editorial,"regla"
    if idioma=="en":
        candidato=traducir(original)
        if candidato:
            return candidato,"traduccion_automatica"
    return original[:260],"original"
