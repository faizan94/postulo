"""Strip contact details and personal lines before a CV is stored (D3, D12). Best effort."""

import re

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE = re.compile(r"(?:(?:\+|00)\d[\d\s/().-]{6,}\d)|(?:\b0\d{2,4}[\s/-]?\d{4,}\b)")
_PERSONAL_LINE = re.compile(
    r"^\s*(geburtsdatum|geburtsort|geboren|date of birth|birth ?date|born|familienstand|"
    r"marital status|staatsangehörigkeit|nationalität|nationality|religion|konfession|"
    r"address|adresse|anschrift|wohnort|telefon|phone|mobil\w*|tel\.?|e-?mail|"
    r"kinder|children|gender|geschlecht)\b.*$",
    re.IGNORECASE | re.MULTILINE,
)
_BLANKS = re.compile(r"\n{3,}")
# Personal profile links identify the person (the account is name-only, D13).
_PROFILE_URL = re.compile(
    r"(?:https?://)?(?:[\w-]+\.)?(?:linkedin\.com/in|xing\.com/profile)/[\w%-]+/?", re.IGNORECASE
)


def clean(text: str) -> str:
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = _PERSONAL_LINE.sub("", t)
    t = _PROFILE_URL.sub("[profile link removed]", t)
    t = _EMAIL.sub("[email removed]", t)
    t = _PHONE.sub("[phone removed]", t)
    t = "\n".join(line.rstrip() for line in t.split("\n"))
    return _BLANKS.sub("\n\n", t).strip()
