"""collect -> filter -> extract -> dedupe/store -> report."""

from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path

from . import report
from .extract import extract
from .models import RawPost, class_key
from .sources import SOURCES
from .sources.manual import inbox_path
from .store import Store

log = logging.getLogger(__name__)

CLASS_WORDS = re.compile(
    r"\b(class(es)?|workshop|lesson|course|camp|demo|hands[- ]on|learn to|masterclass)\b", re.I)
FOOD_WORDS = re.compile(
    r"\b(cook\w*|bak\w*|chef|culinary|kitchen|pasta|sushi|pastry|bread|dumpling|cake|"
    r"cookie|pizza|knife skills|recipe|cuisine|food)\b", re.I)


def looks_relevant(post: RawPost) -> bool:
    """Skip obvious noise before paying for an extraction call."""
    if post.source == "manual":
        return True
    text = f"{post.title}\n{post.text}"
    return bool(CLASS_WORDS.search(text) and FOOD_WORDS.search(text))


def run(cfg: dict, only: list[str] | None = None, dry_run: bool = False, client=None) -> dict:
    root = Path(cfg["_root"])
    store = Store(root / cfg["output"]["data_dir"])
    enabled = [name for name in SOURCES if cfg.get(name, {}).get("enabled", False)]
    if only:
        enabled = [n for n in enabled if n in only]

    posts: list[RawPost] = []
    for name in enabled:
        kwargs = {"client": client} if name == "web_search" and client else {}
        try:
            got = SOURCES[name](cfg, **kwargs)
        except Exception as e:
            log.warning("source %s failed: %s", name, e)
            continue
        log.info("%s: %d posts", name, len(got))
        posts.extend(got)

    # Dedupe within this run, then drop what earlier runs already read.
    unique = {}
    for p in posts:
        unique.setdefault((p.url, p.text[:4000]), p)
    todo = [p for p in unique.values() if not store.is_seen(p)]
    relevant = [p for p in todo if looks_relevant(p)]
    relevant_ids = {id(p) for p in relevant}
    log.info("%d collected, %d unseen, %d pass the keyword filter",
             len(posts), len(todo), len(relevant))

    stats = {"collected": len(posts), "unseen": len(todo), "extracted": 0,
             "classes_found": 0, "new_classes": 0, "errors": 0}
    if dry_run:
        for p in relevant:
            print(f"[{p.source}] {p.url}\n    {p.text[:160]!r}")
        return stats

    new_ids: set[str] = set()
    for p in todo:
        if id(p) not in relevant_ids:
            store.mark_seen(p)
            continue
        try:
            ex = extract(p, cfg, client=client)
        except Exception as e:
            log.warning("extract failed for %s: %s", p.url, e)
            stats["errors"] += 1
            continue  # not marked seen, so it's retried next run
        stats["extracted"] += 1
        store.mark_seen(p)
        if not ex.is_cooking_class_post:
            continue
        for c in ex.classes:
            stats["classes_found"] += 1
            if store.add(c, p):
                new_ids.add(class_key(c))
    stats["new_classes"] = len(new_ids)
    store.save()
    _archive_manual(cfg, [p for p in todo if p.source == "manual" and store.is_seen(p)])

    rows = report.select(store.classes, cfg["output"].get("only_upcoming", True))
    report.write_csv(rows, store.dir / "classes.csv")
    report.write_markdown(rows, new_ids, store.dir / "latest.md")
    log.info("done: %s", stats)
    return stats


def _archive_manual(cfg: dict, done: list[RawPost]) -> None:
    inbox = inbox_path(cfg)
    files = {p.extra.get("file") for p in done} - {None, "posts.jsonl"}
    if not files:
        return
    (inbox / "processed").mkdir(exist_ok=True)
    for name in files:
        src = inbox / name
        if src.exists():
            shutil.move(str(src), str(inbox / "processed" / name))
