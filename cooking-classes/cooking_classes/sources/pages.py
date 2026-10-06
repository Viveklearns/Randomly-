"""Re-check a watchlist of venue / organizer pages (class calendars, link-in-bio pages)."""

from __future__ import annotations

import html
import logging
import re

import requests

from ..models import RawPost

log = logging.getLogger(__name__)

MAX_CHARS = 60_000


def html_to_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style|noscript|svg).*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h\d|tr)>", "\n", raw)
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def collect(cfg: dict, session: requests.Session | None = None) -> list[RawPost]:
    session = session or requests.Session()
    posts = []
    for url in cfg["pages"].get("urls", []):
        try:
            r = session.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
        except Exception as e:
            log.warning("pages: %s failed: %s", url, e)
            continue
        posts.append(RawPost(source="pages", platform="web", url=url,
                             text=html_to_text(r.text)[:MAX_CHARS]))
    return posts
