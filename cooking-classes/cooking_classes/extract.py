"""Turn a RawPost into structured CookingClass records with Claude structured outputs."""

from __future__ import annotations

import datetime as dt
import logging

from .geo import canonical_town
from .llm import FALLBACK_BETA, FALLBACK_BODY, check_refusal, get_client
from .models import Extraction, RawPost

log = logging.getLogger(__name__)

SYSTEM = """You read social media posts and web pages and pull out cooking classes.

A cooking class is any session people can sign up for or attend to learn cooking, baking, \
or food prep: hands-on classes, demos, workshops, kids' cooking camps, private-chef group \
lessons, library or adult-school courses. Restaurant promos, recipes, food reviews, and \
job posts are not classes.

Rules:
- One entry in `classes` per distinct class or session series. Empty list if none.
- Copy facts from the post; use null for anything it doesn't state. Don't guess prices or times.
- Resolve relative dates ("this Saturday") against the post date, or today's date if none.
- in_bergen_county: "yes" if held in a Bergen County, NJ municipality (or online by a \
Bergen County host), "no" if clearly elsewhere, "unknown" if the post doesn't say.
- Note: Oakland, Englewood, Ridgefield, Washington Township etc. also exist outside NJ; \
use context."""


def build_prompt(post: RawPost, today: str) -> str:
    return (
        f"Today: {today}\n"
        f"Source: {post.source} / {post.platform or 'unknown'}\n"
        f"URL: {post.url}\n"
        f"Posted: {post.posted_at or 'unknown'}\n"
        f"Title: {post.title or '-'}\n\n"
        f"<post>\n{post.text}\n</post>"
    )


def extract(post: RawPost, cfg: dict, client=None) -> Extraction:
    client = client or get_client()
    response = client.beta.messages.parse(
        model=cfg["claude"]["model"],
        max_tokens=16000,
        output_config={"effort": cfg["claude"].get("extract_effort", "low")},
        system=SYSTEM,
        messages=[{"role": "user", "content": build_prompt(post, dt.date.today().isoformat())}],
        output_format=Extraction,
        betas=[FALLBACK_BETA],
        extra_body=FALLBACK_BODY,
    )
    check_refusal(response)
    return normalize(response.parsed_output)


def normalize(ex: Extraction) -> Extraction:
    """Cross-check Claude's location call against the municipality list."""
    for c in ex.classes:
        town = canonical_town(c.town)
        if town:
            c.town = town
            if c.in_bergen_county == "unknown" and (c.state or "NJ").upper() in ("NJ", "NEW JERSEY"):
                c.in_bergen_county = "yes"
    return ex
