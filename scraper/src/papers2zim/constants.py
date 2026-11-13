import logging
import os
import pathlib
from typing import Any

from zimscraperlib.logging import getLogger

from papers2zim.__about__ import __version__

ROOT_DIR = pathlib.Path(__file__).parent
NAME = ROOT_DIR.name

VERSION = __version__

SCRAPER = f"{NAME} {VERSION}"


def getenv(key: str, *, mandatory: bool = False, default: Any = None) -> Any:
    value = os.getenv(key) or default

    if mandatory and not value:
        raise OSError(f"Please set the {key} environment variable")

    return value


def parse_bool(value: Any) -> bool:
    """Parse value into boolean."""
    return str(value).lower() in ("true", "1", "yes", "y", "on")


DEBUG = parse_bool(getenv("DEBUG", default="false"))

# Descriptive User-Agent identifying this scraper to every HTTP server we
# talk to. The default python-requests UA is rejected (HTTP 403) by some
# hosts, e.g. Wikimedia's ws-export, whose policy requires identifying the
# client. See https://meta.wikimedia.org/wiki/User-Agent_policy
USER_AGENT = f"{NAME}/{VERSION} (+https://github.com/openzim/papers)"

logger = getLogger(NAME, level=logging.DEBUG if DEBUG else logging.INFO)

DEFAULT_HTTP_TIMEOUT = 10
DL_CHUNCK_SIZE = 8192

LOCALES_LOCATION = pathlib.Path(os.getenv("LOCALES_LOCATION", "./locales"))
