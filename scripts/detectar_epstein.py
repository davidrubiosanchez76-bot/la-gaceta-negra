"""Detector específico y conservador para el expediente CASE EPSTEIN.

Un nombre en un registro de contactos, un vuelo o una fotografía no prueba un
delito. Identificar el asunto del caso no implica imputar delito a terceros.
"""
from __future__ import annotations
import re
import unicodedata


def normalizar(s):
    s = unicodedata.normalize("NFKD", (s or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


CONTEXTOS = (
    "abus", "victim", "victim", "victima", "sex", "trafic", "traffick",
    "court", "trial", "judicial", "juez", "jueza", "tribunal", "juzga", "lawsuit",
    "investig", "polic", "fbi", "arrest", "imput", "cargos", "acus", "charges",
    "sentenc", "senten", "convict", "conden", "suicide", "suicid",
    "death", "muert", "custody", "prision", "prison", "jail",
    "record", "file", "document", "archivo", "expedient", "transcript",
    "public", "liber", "revel", "release", "disclos", "unseal", "desclasific",
    "congress", "congres", "oversight", "fiscal", "justicia", "justice",
    "maxwell", "giuffre", "acosta", "bank", "banco", "settle", "acuerdo",
    "compens", "indemn", "report", "informe", "comite",
)
CRIMINALES = (
    "sex", "abuse", "abus", "trata", "trafic", "traffick", "accus", "acus",
    "convict", "conden", "victim", "victima", "court", "trial", "tribunal",
    "polic", "arrest", "investig", "sentenc", "caso", "case", "justicia",
    "testimony", "testimonio", "document", "archiv", "file",
    "lawmaker", "congress", "congres", "judge", "juez", "jueza",
)


def coincide(titulo, resumen=""):
    t = normalizar(titulo)
    s = normalizar(resumen)
    if re.search(r"epstein[ -]barr|epstein[ -]barr virus", t):
        return False
    # Excluir piezas de ficción y opinión ajena aunque mencionen al acusado.
    if any(x in t for x in ("novel inspired by epstein", "epstein-inspired thriller",
                            "epstein-themed costume")):
        return False
    nombre = bool(re.search(r"\b(?:jeffrey\s+)?epstein\b", t))
    maxwell = bool(re.search(r"\bghislaine\s+maxwell\b", t))
    giuffre = bool(re.search(r"\bvirginia\s+(?:roberts\s+)?giuffre\b", t))
    if nombre:
        return any(x in t for x in CONTEXTOS) or any(x in s for x in CRIMINALES)
    if maxwell or giuffre:
        return any(x in t for x in CRIMINALES) or any(x in s for x in CRIMINALES)
    return False
