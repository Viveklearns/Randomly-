"""Posts you paste in by hand: the route for private Facebook groups and WhatsApp/Nextdoor.

inbox/*.txt   one post per file. An optional first line `URL: https://...` sets the link.
inbox/posts.jsonl   one {"url": ..., "text": ..., "platform": ...} object per line.
Processed files are moved to inbox/processed/ by the pipeline.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from ..models import RawPost

log = logging.getLogger(__name__)


def inbox_path(cfg: dict) -> Path:
    return Path(cfg["_root"]) / cfg["manual"].get("inbox_dir", "inbox")


def collect(cfg: dict) -> list[RawPost]:
    inbox = inbox_path(cfg)
    posts = []
    for f in sorted(inbox.glob("*.txt")):
        body = f.read_text(encoding="utf-8").strip()
        url = ""
        first, _, rest = body.partition("\n")
        if first.lower().startswith("url:"):
            url, body = first[4:].strip(), rest.strip()
        if not body:
            continue
        url = url or "manual:" + hashlib.sha1(body.encode()).hexdigest()[:12]
        posts.append(RawPost(source="manual", platform="manual", url=url, text=body,
                             extra={"file": f.name}))
    jsonl = inbox / "posts.jsonl"
    if jsonl.exists():
        for n, line in enumerate(jsonl.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                log.warning("manual: posts.jsonl line %d is not JSON", n)
                continue
            text = d.get("text", "").strip()
            if not text:
                continue
            url = d.get("url") or "manual:" + hashlib.sha1(text.encode()).hexdigest()[:12]
            posts.append(RawPost(source="manual", platform=d.get("platform", "manual"),
                                 url=url, text=text, posted_at=d.get("posted_at", ""),
                                 extra={"file": "posts.jsonl"}))
    return posts
