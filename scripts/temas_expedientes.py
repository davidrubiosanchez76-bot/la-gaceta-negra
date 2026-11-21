"""Detección prudente del fenómeno de extremismo violento nihilista.

No clasifica por "nihilista" a secas, ni por "terrorismo" a secas,
ni por el número 764 sin contexto. Reduce coincidencias accidentales y
NO determina la calificación jurídico-penal de cada noticia.
"""
from __future__ import annotations
import re
import unicodedata

FUERTES = (
    r"\bnihilistic violent extremis\w*\b",
    r"\bnihilistic extremis\w*\b",
    r"\bnihilistic violence\b",
    r"\bextremismo violento nihilista\b",
    r"\bextremismo nihilista violento\b",
    r"\bextremismo nihilista\b",
    r"\bviolencia nihilista\b",
    r"\bterrorismo nihilista\b",
    r"\bnihilistic terrorist\w*\b",
    r"\b(?:no lives matter|maniac murder cult)\b",
)
CONTEXTO = re.compile(
    r"\b(extremis\w*|nihilis\w*|violent\w*|violenc\w*|terroris\w*|"
    r"sextor\w*|explotaci\w*|exploitat\w*|child abuse|coerc\w*|"
    r"chantaj\w*|criminal\w*|amenaz\w*|threat\w*|"
    r"gang|"
    r"radicaliza\w*|detenid\w*|acusa\w*|charged|arrest\w*|sentenc\w*|conden\w*)\b"
)
AMBIGUO = (r"\b764\b", r"\bthe com\b", r"\bcom network\b")

def normalizar(texto):
    s = unicodedata.normalize("NFKD", (texto or "").lower())
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", s)

def coincide(texto, resumen=""):
    texto = normalizar(texto)
    resumen = normalizar(resumen)
    combinado = texto + " " + resumen
    if any(re.search(p, texto) for p in FUERTES):
        return True
    # Un título que sólo menciona un número o la palabra "Com"
    # no basta; se necesita el contexto criminológico en la misma pieza.
    if any(re.search(p, texto) for p in AMBIGUO) and CONTEXTO.search(combinado):
        return True
    # RSS de prensa a veces omiten el término técnico en el titular.
    if any(re.search(p, resumen) for p in FUERTES):
        return CONTEXTO.search(texto) is not None or bool(re.search(r"\b(?:764|the com)\b", texto))
    return False
