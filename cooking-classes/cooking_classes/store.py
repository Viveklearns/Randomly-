"""JSON-file storage: data/classes.json (results) and data/seen.json (processed posts)."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

from .models import CookingClass, RawPost, class_key


def post_fingerprint(post: RawPost) -> str:
    """Same URL with changed content (an updated calendar page) gets re-read."""
    return hashlib.sha1(f"{post.url}|{post.text[:4000]}".encode()).hexdigest()[:20]


class Store:
    def __init__(self, data_dir: Path):
        self.dir = Path(data_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.classes: dict[str, dict] = self._load("classes.json", {})
        self.seen: dict[str, str] = self._load("seen.json", {})

    def _load(self, name, default):
        p = self.dir / name
        return json.loads(p.read_text()) if p.exists() else default

    def is_seen(self, post: RawPost) -> bool:
        return post_fingerprint(post) in self.seen

    def mark_seen(self, post: RawPost) -> None:
        self.seen[post_fingerprint(post)] = post.url

    def add(self, c: CookingClass, post: RawPost) -> bool:
        """Insert or merge. Returns True if this is a class we hadn't seen before."""
        key = class_key(c)
        now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        rec = self.classes.get(key)
        if rec is None:
            self.classes[key] = {
                "id": key, **c.model_dump(),
                "sources": [{"url": post.url, "platform": post.platform, "source": post.source}],
                "first_seen": now, "last_seen": now,
            }
            return True
        # Fill gaps from the new sighting, keep the first non-null value otherwise.
        for field, value in c.model_dump().items():
            if rec.get(field) in (None, "", "unknown") and value not in (None, ""):
                rec[field] = value
        if post.url not in {s["url"] for s in rec["sources"]}:
            rec["sources"].append({"url": post.url, "platform": post.platform, "source": post.source})
        rec["last_seen"] = now
        return False

    def save(self) -> None:
        (self.dir / "classes.json").write_text(json.dumps(self.classes, indent=2, sort_keys=True))
        (self.dir / "seen.json").write_text(json.dumps(self.seen, indent=2, sort_keys=True))
