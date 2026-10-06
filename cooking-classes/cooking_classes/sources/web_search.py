"""Discovery via Claude's web search tool.

Facebook and Instagram have no public post-search API, but their public
events/posts are indexed by search engines. Claude searches, reads results,
and returns each distinct post or event page it found.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import re

from ..llm import create_with_server_tools, get_client, text_of
from ..models import RawPost

log = logging.getLogger(__name__)

SYSTEM = """You find cooking classes advertised online for people in Bergen County, New Jersey.

Search the web for the request you are given. Prefer individual posts and event pages \
(facebook.com/events, facebook.com posts, instagram.com/p/..., eventbrite.com/e/..., \
allevents.in, meetup.com, patch.com, library and town calendars) over generic directory pages. \
Include classes in Bergen County towns, and online classes run by Bergen County hosts. \
Skip anything that clearly already happened before {today}.

When done searching, reply with only a JSON array (no prose, no code fence). One element per \
post or event page:
{{"url": str, "platform": str, "title": str, "posted_at": str or "", \
"text": str  // everything the page says about the class: dates, times, place, price, host, how to sign up
}}
Return [] if you found nothing relevant. Only include URLs you actually saw in search results."""


def parse_json_array(text: str) -> list[dict]:
    """Tolerate a stray code fence or sentence around the array."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end < start:
        return []
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        log.warning("web_search: could not parse JSON from Claude reply")
        return []
    return [d for d in data if isinstance(d, dict) and d.get("url")]


def collect(cfg: dict, client=None) -> list[RawPost]:
    ws = cfg["web_search"]
    client = client or get_client()
    today = dt.date.today().isoformat()
    tools = [{
        "type": "web_search_20260209",
        "name": "web_search",
        "max_uses": ws.get("max_searches_per_query", 6),
        "user_location": {
            "type": "approximate",
            "city": "Hackensack",
            "region": "New Jersey",
            "country": "US",
            "timezone": "America/New_York",
        },
    }]
    posts: list[RawPost] = []
    for query in ws["queries"]:
        log.info("web_search: %s", query)
        try:
            response = create_with_server_tools(
                client,
                model=cfg["claude"]["model"],
                max_tokens=16000,
                output_config={"effort": cfg["claude"].get("search_effort", "medium")},
                system=SYSTEM.format(today=today),
                tools=tools,
                messages=[{"role": "user", "content": query}],
            )
        except Exception as e:  # one bad query shouldn't sink the run
            log.warning("web_search failed for %r: %s", query, e)
            continue
        for item in parse_json_array(text_of(response)):
            posts.append(RawPost(
                source="web_search",
                url=item["url"],
                platform=item.get("platform", ""),
                title=item.get("title", ""),
                posted_at=item.get("posted_at", ""),
                text=item.get("text", ""),
                extra={"query": query},
            ))
    return posts
