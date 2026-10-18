"""One normalization layer: the "tokenized" form of skills, job titles and places.

Every comparison of names goes through here, so spelling and case never block a match:
"REACT" = "react" = "React"; "Node JS" = "Node.js" = "nodejs"; "München" = "Muenchen" =
"Munchen"; "Softwareentwickler" ~ "Software Engineer"; "Sr. ML Eng" ~ "Senior ML Engineer".
Display text is never changed; only the comparison keys are.
"""

import re
import unicodedata

_WS = re.compile(r"\s+")
_KEEP = re.compile(r"[^a-z0-9+#]")
_UMLAUT_E = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue"})


def fold(text: str) -> str:
    """Lowercase, accents removed (ü -> u, é -> e, ß -> ss), whitespace collapsed."""
    t = unicodedata.normalize("NFKD", text.replace("ß", "ss").replace("ẞ", "SS"))
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    return _WS.sub(" ", t).casefold().strip()


def key(text: str) -> str:
    """Comparison key for a skill or term: folded, only letters, digits, '+' and '#'.

    'Node.js', 'Node JS' and 'NodeJS' -> 'nodejs'; 'C++' -> 'c++'; 'C#' -> 'c#'.
    """
    return _KEEP.sub("", fold(text))


def spelling_variants(text: str) -> set[str]:
    """Ways a German/accented word is written: 'München' -> {münchen, munchen, muenchen}."""
    low = text.casefold()
    return {low, fold(low), low.translate(_UMLAUT_E).casefold()}


# --- job titles ---------------------------------------------------------------------------

_GENDER = re.compile(
    r"\((?:[mwfdxai]\s*[/|,]\s*)+[mwfdxai]\)|\(all genders?\)|\(gn\)|\*in\b|:in\b|/in\b", re.I
)
_PHRASES = [  # applied to folded text, separators already turned into spaces
    (re.compile(r"\bfront ?end\b"), "frontend"),
    (re.compile(r"\bback ?end\b"), "backend"),
    (re.compile(r"\bfull ?stack\b"), "fullstack"),
    (re.compile(r"\bdev ?ops\b"), "devops"),
    (re.compile(r"\bdev ?sec ?ops\b"), "devsecops"),
    (re.compile(r"\bml ?ops\b"), "mlops"),
    (re.compile(r"\bmachine learning\b"), "ml"),
    (re.compile(r"\bartificial intelligence\b"), "ai"),
    (re.compile(r"\bkunstliche intelligenz\b"), "ai"),
    (re.compile(r"\bki\b"), "ai"),
    (re.compile(r"\bgen ?ai\b"), "genai"),
    (re.compile(r"\bsite reliability\b"), "sre"),
    (re.compile(r"\bquality assurance\b"), "qa"),
    (re.compile(r"\bbusiness intelligence\b"), "bi"),
]
ABBREVIATIONS = {
    "sr": "senior",
    "snr": "senior",
    "jr": "junior",
    "jnr": "junior",
    "eng": "engineer",
    "engr": "engineer",
    "engg": "engineer",
    "dev": "developer",
    "devs": "developer",
    "mgr": "manager",
    "mngr": "manager",
    "swe": "software engineer",
    "sde": "software engineer",
    "pm": "product manager",
}
# German compound role words: "softwareentwickler" -> "software entwickler"
_ROLE_SUFFIXES = (
    "entwicklerin",
    "entwickler",
    "ingenieurin",
    "ingenieur",
    "architektin",
    "architekt",
    "analystin",
    "analyst",
    "engineer",
    "developer",
    "administrator",
    "beraterin",
    "berater",
    "managerin",
    "manager",
    "designerin",
    "designer",
    "wissenschaftler",
    "programmierer",
)


def _split_compound(word: str) -> list[str]:
    for suffix in _ROLE_SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return [word[: -len(suffix)], suffix]
    return [word]


def title_tokens(title: str) -> list[str]:
    """Normalized word tokens of a job title (gender marks removed, variants unified)."""
    t = fold(_GENDER.sub(" ", title))
    t = re.sub(r"[-_/.,()|&+:]", " ", t.replace("c++", "cpp").replace("c#", "csharp"))
    t = _WS.sub(" ", t).strip()
    for pat, repl in _PHRASES:
        t = pat.sub(repl, t)
    out: list[str] = []
    for w in t.split():
        expanded = ABBREVIATIONS.get(w, w)
        for part in expanded.split():
            out.extend(_split_compound(part))
    return out
