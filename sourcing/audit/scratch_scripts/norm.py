import re, unicodedata
from unidecode import unidecode
_ws = re.compile(r"\s+")
_punct = re.compile(r"[^a-z0-9 ]+")
def norm(s: str) -> str:
    s = unidecode(unicodedata.normalize("NFKC", s)).lower()
    s = s.replace("&", " and ")
    s = _punct.sub(" ", s)
    return _ws.sub(" ", s).strip()
def norm_author(s: str) -> str:
    s = norm(s)
    s = re.sub(r"\b(sir|lord|dr|st|saint|mr|mrs)\b", " ", s)
    return _ws.sub(" ", s).strip()
