import re

# --- Specialty keywords (German terms, since German job boards use German titles) ---

TRAUMA_KEYWORDS = [
    "unfallchirurgie", "unfallchirurgisch", "traumatologie", "trauma surgery",
    "polytrauma", "orthopädie und unfallchirurgie", "orthopädie/unfallchirurgie",
    "d-arzt", "durchgangsarzt", "bg-klinik", "bg klinik", "berufsgenossenschaft",
]

ORTHO_TRAUMA_KEYWORDS = [
    "orthopädie und unfallchirurgie", "orthopädie/unfallchirurgie", "o&u",
    "orthopädische chirurgie", "orthopädie", "orthopädisch",
]

GENERAL_SURGERY_KEYWORDS = [
    "allgemeinchirurgie", "allgemein- und viszeralchirurgie", "viszeralchirurgie",
    "visceralchirurgie", "abdominalchirurgie", "general surgery",
]

VASCULAR_KEYWORDS = ["gefäßchirurgie", "gefaesschirurgie", "vascular surgery"]
THORACIC_KEYWORDS = ["thoraxchirurgie", "thoracic surgery"]
CARDIAC_KEYWORDS = ["herzchirurgie", "kardiochirurgie", "cardiac surgery"]
PEDIATRIC_SURGERY_KEYWORDS = ["kinderchirurgie", "pediatric surgery"]
PLASTIC_SURGERY_KEYWORDS = ["plastische chirurgie", "plastische und ästhetische chirurgie", "plastic surgery"]
NEUROSURGERY_KEYWORDS = ["neurochirurgie", "neurosurgery"]

# Broad "is this surgery at all" catch-all — used to decide relevance
SURGERY_KEYWORDS = (
    ["chirurgie", "chirurgisch", "chirurg", "surgery", "surgical"]
    + TRAUMA_KEYWORDS + GENERAL_SURGERY_KEYWORDS + VASCULAR_KEYWORDS
    + THORACIC_KEYWORDS + CARDIAC_KEYWORDS + PEDIATRIC_SURGERY_KEYWORDS
    + PLASTIC_SURGERY_KEYWORDS + NEUROSURGERY_KEYWORDS
)

# --- Training level keywords ---

ASSISTENZARZT_KEYWORDS = [
    "assistenzarzt", "assistenzärztin", "assistenzaerztin", "arzt in weiterbildung",
    "ärztin in weiterbildung", "weiterbildungsassistent", "aiw", "arzt/ärztin in weiterbildung",
]

FACHARZT_KEYWORDS = [
    "facharzt", "fachärztin", "fachaerztin", "facharztstandard",
]

ROTATION_KEYWORDS = [
    "common trunk", "rotationsstelle", "rotation", "basisweiterbildung",
]

# Job-posting-ish and location/exclusion helpers

EXCLUDE_KEYWORDS = [
    # roles that mention "chirurgie" but aren't physician residency roles we want
    "pflegefachkraft", "pflegekraft", "study nurse", "arzthelfer", "mfa ",
    "medizinische fachangestellte", "op-schwester", "op-pfleger", "famulatur",
    "pj-", "praktikum", "ausbildung zum", "ausbildung zur",
]

BERLIN_AREA_KEYWORDS = [
    "berlin", "brandenburg", "potsdam", "spandau", "neukölln", "neukoelln",
    "friedrichshain", "kreuzberg", "charlottenburg", "steglitz", "zehlendorf",
    "reinickendorf", "pankow", "lichtenberg", "marzahn", "tempelhof",
    "köpenick", "koepenick", "mitte", "wedding", "buch",
]


def _has_any(text: str, keywords) -> bool:
    return any(kw in text for kw in keywords)


def is_relevant(text: str) -> bool:
    """True if this looks like a physician surgical-residency job, not noise."""
    lower = text.lower()
    if _has_any(lower, EXCLUDE_KEYWORDS):
        return False
    has_surgery = _has_any(lower, SURGERY_KEYWORDS)
    has_level = _has_any(lower, ASSISTENZARZT_KEYWORDS + FACHARZT_KEYWORDS + ROTATION_KEYWORDS)
    return has_surgery and has_level


def is_berlin_area(text: str) -> bool:
    lower = text.lower()
    return _has_any(lower, BERLIN_AREA_KEYWORDS)


def extract_specialty(text: str) -> list:
    lower = text.lower()
    specs = []
    if _has_any(lower, TRAUMA_KEYWORDS):
        specs.append("trauma")
    if _has_any(lower, ORTHO_TRAUMA_KEYWORDS):
        specs.append("orthopedic_trauma")
    if _has_any(lower, GENERAL_SURGERY_KEYWORDS):
        specs.append("general_surgery")
    if _has_any(lower, VASCULAR_KEYWORDS):
        specs.append("vascular")
    if _has_any(lower, THORACIC_KEYWORDS):
        specs.append("thoracic")
    if _has_any(lower, CARDIAC_KEYWORDS):
        specs.append("cardiac")
    if _has_any(lower, PEDIATRIC_SURGERY_KEYWORDS):
        specs.append("pediatric_surgery")
    if _has_any(lower, PLASTIC_SURGERY_KEYWORDS):
        specs.append("plastic_surgery")
    if _has_any(lower, NEUROSURGERY_KEYWORDS):
        specs.append("neurosurgery")
    if not specs and _has_any(lower, SURGERY_KEYWORDS):
        specs.append("surgery_other")
    return specs


def extract_level(text: str) -> list:
    lower = text.lower()
    levels = []
    if _has_any(lower, ASSISTENZARZT_KEYWORDS):
        levels.append("assistenzarzt")
    if _has_any(lower, FACHARZT_KEYWORDS):
        levels.append("facharzt")
    if _has_any(lower, ROTATION_KEYWORDS):
        levels.append("rotation")
    return levels


# Common non-German-market noise domains to skip in search-based scraping
SKIP_DOMAINS = [
    "twitter.com", "x.com", "facebook.com", "instagram.com",
    "linkedin.com", "youtube.com", "wikipedia.org", "reddit.com",
    "pinterest.com", "tiktok.com", "xing.com",
]
