"""Creative Commons license identifiers.

Sources describe licenses in different ways: the Wikisource OPDS feed gives a
URI (`http://creativecommons.org/licenses/by-sa/3.0`), the Open Textbook Library
gives a name without a version (`Attribution-NonCommercial-ShareAlike`), and
One More Library gives a short code (`CC BY-SA 4.0`). This module reduces all of
them to one identifier, so that the UI can build a localized label and a link
from it instead of displaying whatever string the source provided.

Versioned licenses use their SPDX identifier (`CC-BY-SA-3.0`, `CC0-1.0`). The
Open Textbook Library does not say which version applies, so its licenses get an
unversioned identifier (`CC-BY-NC-SA`): it is not valid SPDX, but it claims no
more than the source did, and it has no canonical URL.

Only licenses that can be identified without guessing are recognized. Anything
else (other families, jurisdiction-specific Creative Commons ports, free text
such as Project Gutenberg's) yields `None`, and callers keep displaying the
source's own text.
"""

import re

_TERMS = r"BY(?:-NC)?(?:-ND|-SA)?"
_VERSION = r"\d\.\d"
_DEED = r"(?:/(?:deed|legalcode)(?:\.[\w-]+)?)?/?"

_CC_URI = re.compile(
    rf"https?://(?:www\.)?creativecommons\.org/licenses/"
    rf"(?P<terms>{_TERMS})/(?P<version>{_VERSION}){_DEED}",
    re.IGNORECASE,
)
_CC0_URI = re.compile(
    rf"https?://(?:www\.)?creativecommons\.org/publicdomain/zero/1\.0{_DEED}",
    re.IGNORECASE,
)
_CC_CODE = re.compile(
    rf"CC[ -](?P<terms>{_TERMS})(?:[ -](?P<version>{_VERSION}))?",
    re.IGNORECASE,
)
_CC0_CODE = re.compile(r"CC0(?:[ -]1\.0)?(?: Universal)?", re.IGNORECASE)

# Creative Commons license names as given without a version number
_CC_NAMES = {
    "attribution": "BY",
    "attribution-noncommercial": "BY-NC",
    "attribution-noncommercial-noderivs": "BY-NC-ND",
    "attribution-noncommercial-sharealike": "BY-NC-SA",
    "attribution-noderivs": "BY-ND",
    "attribution-sharealike": "BY-SA",
}

_CC_ID = re.compile(rf"CC-(?P<terms>{_TERMS})(?:-(?P<version>{_VERSION}))?")
_CC0_ID = "CC0-1.0"

_TERM_LABELS = {
    "BY": "Attribution",
    "NC": "NonCommercial",
    "ND": "NoDerivatives",
    "SA": "ShareAlike",
}


def _cc_identifier(terms: str, version: str | None) -> str:
    return f"CC-{terms.upper()}-{version}" if version else f"CC-{terms.upper()}"


def license_identifier(value: str | None) -> str | None:
    """Return the identifier of the Creative Commons license `value` names.

    `value` may be a license URI, a short code or a license name. Returns `None`
    when it is not a Creative Commons license this module can identify.
    """
    if not value or not (value := value.strip()):
        return None
    if uri := _CC_URI.fullmatch(value):
        return _cc_identifier(uri["terms"], uri["version"])
    if _CC0_URI.fullmatch(value) or _CC0_CODE.fullmatch(value):
        return _CC0_ID
    if code := _CC_CODE.fullmatch(value):
        return _cc_identifier(code["terms"], code["version"])
    if terms := _CC_NAMES.get(value.casefold()):
        return _cc_identifier(terms, None)
    return None


def license_url(license_id: str) -> str | None:
    """Return the canonical HTTPS page describing the license, if it has one."""
    if license_id == _CC0_ID:
        return "https://creativecommons.org/publicdomain/zero/1.0/"
    if (match := _CC_ID.fullmatch(license_id)) and match["version"]:
        return (
            f"https://creativecommons.org/licenses/"
            f"{match['terms'].lower()}/{match['version']}/"
        )
    return None


def license_label(license_id: str) -> str | None:
    """Return the English name of a license, e.g. for the No-JS pages.

    The UI builds its own localized label from the same identifier.
    """
    if license_id == _CC0_ID:
        return "CC0 1.0 Universal"
    if not (match := _CC_ID.fullmatch(license_id)):
        return None
    terms = match["terms"]
    name = "-".join(_TERM_LABELS[term] for term in terms.split("-"))
    version = f" {match['version']}" if match["version"] else ""
    return f"Creative Commons {name}{version} (CC {terms}{version})"
