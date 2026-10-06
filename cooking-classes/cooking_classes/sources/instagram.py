"""Instagram hashtag search through the official Instagram Graph API.

Requirements (one-time, free):
  1. An Instagram Business or Creator account, linked to a Facebook Page.
  2. A Meta developer app with the `instagram_basic` permission and access to
     the Instagram Public Content Access feature.
  3. Env vars IG_USER_ID (the IG business account id) and IG_ACCESS_TOKEN.
Meta caps you at 30 unique hashtags per rolling 7 days.
"""

from __future__ import annotations

import logging
import os

import requests

from ..models import RawPost

log = logging.getLogger(__name__)

GRAPH = "https://graph.facebook.com/v21.0"


def collect(cfg: dict, session: requests.Session | None = None) -> list[RawPost]:
    user_id, token = os.environ.get("IG_USER_ID"), os.environ.get("IG_ACCESS_TOKEN")
    if not (user_id and token):
        log.info("instagram: IG_USER_ID / IG_ACCESS_TOKEN not set, skipping")
        return []
    session = session or requests.Session()
    posts: dict[str, RawPost] = {}
    for tag in cfg["instagram"]["hashtags"]:
        try:
            r = session.get(f"{GRAPH}/ig_hashtag_search",
                            params={"user_id": user_id, "q": tag, "access_token": token},
                            timeout=20)
            r.raise_for_status()
            ids = [h["id"] for h in r.json().get("data", [])]
            if not ids:
                continue
            r = session.get(f"{GRAPH}/{ids[0]}/recent_media",
                            params={"user_id": user_id, "access_token": token, "limit": 50,
                                    "fields": "id,caption,permalink,timestamp,media_type"},
                            timeout=20)
            r.raise_for_status()
        except Exception as e:
            log.warning("instagram #%s failed: %s", tag, e)
            continue
        for m in r.json().get("data", []):
            caption = m.get("caption") or ""
            if not caption or not m.get("permalink"):
                continue
            posts[m["permalink"]] = RawPost(
                source="instagram",
                platform="instagram",
                url=m["permalink"],
                text=caption,
                posted_at=m.get("timestamp", ""),
                extra={"hashtag": tag},
            )
    return list(posts.values())
