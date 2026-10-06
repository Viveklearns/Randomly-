"""Writes data/classes.csv and data/latest.md from the store."""

from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path

CSV_FIELDS = [
    "start_date", "start_time", "end_time", "title", "host", "town", "venue", "address",
    "price", "audience", "cuisine_or_topic", "recurrence", "is_online", "in_bergen_county",
    "registration_url", "contact", "description", "source_urls", "first_seen", "id",
]


def select(classes: dict, only_upcoming: bool, today: dt.date | None = None) -> list[dict]:
    today = today or dt.date.today()
    rows = []
    for rec in classes.values():
        if rec.get("in_bergen_county") == "no":
            continue
        d = rec.get("start_date")
        # Recurring classes and undated posts stay listed; dated past ones drop off.
        if only_upcoming and d and d < today.isoformat() and not rec.get("recurrence"):
            continue
        rows.append(rec)
    return sorted(rows, key=lambda r: (r.get("start_date") or "9999", r.get("start_time") or ""))


def write_csv(rows: list[dict], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({**r, "source_urls": " ".join(s["url"] for s in r["sources"])})


def _cell(s) -> str:
    return str(s or "").replace("|", "/").replace("\n", " ")


def write_markdown(rows: list[dict], new_ids: set[str], path: Path) -> None:
    today = dt.date.today().isoformat()
    lines = [
        "# Bergen County cooking classes",
        "",
        f"Updated {today}. {len(rows)} classes listed, {len(new_ids)} new this run (marked 🆕).",
        "Location marked `?` means the post didn't say where; check before signing up.",
        "",
        "| Date | Time | Class | Host | Town | Price | For | Link |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        link = r.get("registration_url") or r["sources"][0]["url"]
        town = r.get("town") or ("Online" if r.get("is_online") else "")
        if r.get("in_bergen_county") == "unknown":
            town = f"{town} ?".strip()
        when = r.get("start_date") or r.get("recurrence") or "TBA"
        lines.append(
            f"| {_cell(when)} | {_cell(r.get('start_time'))} "
            f"| {'🆕 ' if r['id'] in new_ids else ''}{_cell(r['title'])} "
            f"| {_cell(r.get('host'))} | {_cell(town)} | {_cell(r.get('price'))} "
            f"| {_cell(r.get('audience'))} | [link]({link}) |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
