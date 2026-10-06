"""Reddit public search JSON (no auth needed for light use)."""

from __future__ import annotations

import datetime as dt
import logging

import requests

from ..models import RawPost

log = logging.getLogger(__name__)

USER_AGENT = "bergen-cooking-classes/0.1 (personal research script)"


def collect(cfg: dict, session: requests.Session | None = None) -> list[RawPost]:
    rc = cfg["reddit"]
    session = session or requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    posts: dict[str, RawPost] = {}
    for sub in rc["subreddits"]:
        for term in rc["search_terms"]:
            url = f"https://www.reddit.com/r/{sub}/search.json"
            params = {"q": f'"{term}"', "restrict_sr": 1, "sort": "new",
                      "t": rc.get("time_window", "month"), "limit": 50}
            try:
                r = session.get(url, params=params, timeout=20)
                r.raise_for_status()
                children = r.json()["data"]["children"]
            except Exception as e:
                log.warning("reddit r/%s %r failed: %s", sub, term, e)
                continue
            for child in children:
                d = child["data"]
                link = "https://www.reddit.com" + d["permalink"]
                posts[link] = RawPost(
                    source="reddit",
                    platform="reddit",
                    url=link,
                    title=d.get("title", ""),
                    text=f"{d.get('title', '')}\n\n{d.get('selftext', '')}\n{d.get('url', '')}",
                    posted_at=dt.datetime.fromtimestamp(
                        d.get("created_utc", 0), dt.timezone.utc).isoformat(),
                    extra={"subreddit": sub},
                )
    return list(posts.values())
