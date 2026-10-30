"""Language names used by One More Library mapped to ISO 639 codes.

The site labels books with language autonyms ("Français", "Русский", ...)
instead of ISO codes. The set below is the full list advertised on
``/index.php/en/languages``; anything else is reported as unknown.
"""

from papers2zim.core.utils import normalize

LANGUAGE_CODES = {
    "english": "en",
    "español": "es",
    "français": "fr",
    "deutsch": "de",
    "italiano": "it",
    "العربية": "ar",
    "русский": "ru",
    "suomi": "fi",
    "svenska": "sv",
    "lingua latīna": "la",
    "latina": "la",
    "latin": "la",
    "αρχαία ελληνική γλώσσα": "grc",
    "ancient greek": "grc",
}


def normalize_language_name(name: str) -> str:
    """Normalize a language label so case and Unicode form do not matter."""
    return (normalize(name) or "").strip().casefold()


def language_code(name: str | None) -> str | None:
    """Return the ISO 639 code for a One More Library language label."""
    if not name:
        return None
    return LANGUAGE_CODES.get(normalize_language_name(name))
