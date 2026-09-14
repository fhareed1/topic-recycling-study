"""Shared HTTP helpers. Standard library only, so the study runs on a slow link without pip."""

import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path

import truststore

# Verify certificates against the operating system trust store. Python's bundled CA list
# rejects repository.ui.edu.ng (expired chain) while the OS store validates an alternate chain.
TLS_CONTEXT = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

USER_AGENT = (
    "topic-recycling-study/0.1 (academic measurement study; "
    "+https://github.com/fhareed1/topic-recycling-study)"
)
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"


def fetch(url: str, delay: float = 2.0, retries: int = 4, timeout: int = 120) -> bytes:
    """GET a URL politely: fixed delay before every request, exponential backoff on failure."""
    last_error = None
    for attempt in range(retries):
        time.sleep(delay * (2**attempt))
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=timeout, context=TLS_CONTEXT) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            last_error = error
            print(f"  retry {attempt + 1}/{retries} for {url}: {error}")
    raise RuntimeError(f"failed to fetch {url}") from last_error
