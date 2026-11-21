"""Reformulación conservadora y fiel de titulares de La Gaceta Negra.

Ninguna regla inventa datos: sólo reorganiza hechos expresos en el titular RSS.
Si no hay una transformación inequívoca se conserva el original y se señala
metodo='original'. El reemplazo de TODO titular por prosa editorial, incluida
la traducción libre, requiere un modelo de lenguaje con validación adicional.
"""
from __future__ import annotations
import re
import unicodedata

def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(ch for ch in s if not unicodedata.combining(ch))

def compose(t):
    t = re.sub(r"\s+", " ", t).strip().strip(".")
    return t[0].upper() + t[1:] if t else t

def validar(original, nuevo):
    if not nuevo or len(nuevo) < 28 or len(nuevo) > 165 or norm(nuevo) == norm(original):
        return False
    # Las cifras son hechos especialmente fáciles de perder o tergiversar.
    figures = set(re.findall(r"\b\d+\b", original))
    if figures and not figures.issubset(set(re.findall(r"\b\d+\b", nuevo))):
        return False
    a, b = norm(original), norm(nuevo)
    # Nunca convertir una sospecha o acusación en afirmación de culpabilidad.
    provisional = ("presunt", "sospech", "acusad", "supuest", "alleged", "accused",
                   "reportedly", "claims", "investigad", "suspicious", "would have")
    reserves = ("presunt", "sospech", "acusad", "supuest", "habria",
                "investigad", "segun", "acusa", "atribuye", "senala", "cree")
    if any(w in a for w in provisional) and not any(w in b for w in reserves):
        return False
    return True

def reescribir_titular(titulo, categoria="TRUE CRIME"):
    """(titular, metodo): 'regla' si se ha transformado con fidelidad; 'original' si no."""
    t = re.sub(r"\s+", " ", titulo or "").strip()
    if not t:
        return t, "original"

    # Se aplican únicamente patrones con significado inequívoco.
    rules = [
        (r"^Detenid[oa] (?:un hombre |una mujer )?por (?:el )?(?P<qual>presunto )?(?P<delito>apuñalamiento|asesinato|homicidio) de (?P<victima>su esposa|su marido|su pareja|su expareja) en (?P<lugar>[\wÀ-ÿ \-]+)$",
         lambda m: f"{m['lugar']}: detención por el {m['qual'] or ''}{m['delito']} de {m['victima']}"),
        (r"^Detenid[oa] un hombre por presuntamente matar a su (?P<parentesco>madre|padre|esposa|pareja) en (?P<lugar>[\wÀ-ÿ \-]+?)(?: este lunes| este martes| este miércoles| este jueves| este viernes| este sábado| este domingo)?$",
         lambda m: f"{m['lugar']}: detenido un hombre por la presunta muerte de su {m['parentesco']}"),
        (r"^Un hombre asesina a su pareja en (?P<lugar>[\wÀ-ÿ \-]+) y se entrega a la policía$",
         lambda m: f"{m['lugar']}: un hombre se entrega a la policía tras matar a su pareja"),
        (r"^Detenidos (?P<num>dos|tres|cuatro|\d+) pasajeros en el aeropuerto de (?P<lugar>El Prat|Barcelona|Madrid|Málaga) con (?P<cantidad>\d+) bolas de cocaína en su cuerpo$",
         lambda m: f"{m['lugar']}: {m['num']} pasajeros detenidos con {m['cantidad']} bolas de cocaína en el cuerpo"),
        (r"^Detenid[oa] un hombre por una presunta agresión sexual en la zona de (?P<lugar>la Sagrada Familia|las Ramblas|el Raval)$",
         lambda m: f"{m['lugar']}: detenido un hombre por una presunta agresión sexual"),
        (r"^Detenid[oa] por (?P<num>\w+) atracos violentos en establecimientos de (?P<lugar>Barcelona|Madrid|Valencia|Girona)$",
         lambda m: f"{m['lugar']}: una detención por {m['num']} atracos violentos en establecimientos"),
        (r"^Detenido en (?P<lugar>Granada|Madrid|Barcelona|Valencia) al hombre acusado de disparar contra (?P<victimas>.+?)(?: en octubre)?$",
         lambda m: f"{m['lugar']}: detenido el hombre acusado de disparar contra {m['victimas']}"),
        (r"^Prisión para (?P<num>\w+) de los detenidos por (?P<razon>.+) en (?P<lugar>Barcelona|Madrid|Girona)$",
         lambda m: f"{m['lugar']}: prisión para {m['num']} detenidos por {m['razon']}"),
        (r"^Detenid[oa] por (?P<delito>robar con violencia .+?) en (?P<lugar>Barcelona|Madrid|Girona|Valencia)$",
         lambda m: f"{m['lugar']}: detención por {m['delito']}"),
        (r"^Man convicted of starting (?P<fire>.+?) fire in (?P<lugar>Los Angeles|New York|California)$",
         lambda m: f"Condenado un hombre por provocar el incendio de {m['fire']} en {('Los Ángeles' if m['lugar']=='Los Angeles' else m['lugar'])}"),
        (r"^French police officers sentenced for beating of music producer (?P<persona>.+)$",
         lambda m: f"Condenados policías franceses por agredir al productor musical {m['persona']}"),
        (r"^Denmark accuses Russia of plotting to assassinate US-Ukrainian rapper$",
         lambda m: "Dinamarca acusa a Rusia de planear el asesinato de un rapero ucraniano-estadounidense"),
        (r"^Florida pastor found guilty over (?P<year>\d{4}) assassination of Haitian president$",
         lambda m: f"Declaran culpable a un pastor de Florida por el asesinato del presidente de Haití en {m['year']}"),
        (r"^Teenager allegedly organised arsons and kidnapping on Signal during Melbourne hospitality wars$",
         lambda m: "Un adolescente habría organizado incendios provocados y un secuestro por Signal durante conflictos hosteleros en Melbourne"),
    ]
    for pattern, transform in rules:
        m = re.fullmatch(pattern, t, flags=re.IGNORECASE)
        if m:
            candidate = compose(transform(m))
            if validar(t, candidate):
                return candidate, "regla"
    return t, "original"
