"""Data shapes shared across the pipeline."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Literal, Optional

from pydantic import BaseModel, Field


@dataclass
class RawPost:
    """A candidate post/page from any source, before Claude has looked at it."""

    source: str  # "web_search", "reddit", "instagram", "manual", "pages"
    url: str
    text: str
    platform: str = ""  # facebook, instagram, eventbrite, reddit, ...
    title: str = ""
    posted_at: str = ""  # ISO date/time if the source gives one
    extra: dict = field(default_factory=dict)


class CookingClass(BaseModel):
    """One class/session pulled out of a post. Unknown fields stay null."""

    title: str = Field(description="Short name of the class, e.g. 'Hands-on Pasta Making'")
    host: Optional[str] = Field(description="Person, business, or organization running it")
    description: Optional[str] = Field(description="One or two sentence summary")
    cuisine_or_topic: Optional[str] = Field(description="e.g. Italian, baking, knife skills")
    start_date: Optional[str] = Field(description="ISO date YYYY-MM-DD of the (first) session")
    start_time: Optional[str] = Field(description="24h HH:MM local time")
    end_time: Optional[str] = Field(description="24h HH:MM local time")
    recurrence: Optional[str] = Field(description="e.g. 'Every Tuesday', '4-week series'")
    venue: Optional[str]
    address: Optional[str]
    town: Optional[str] = Field(description="Municipality name, e.g. 'Ridgewood'")
    state: Optional[str]
    is_online: bool
    in_bergen_county: Literal["yes", "no", "unknown"]
    price: Optional[str] = Field(description="As written, e.g. '$65/person', 'Free'")
    audience: Optional[str] = Field(description="adults, kids, teens, families, seniors...")
    registration_url: Optional[str]
    contact: Optional[str] = Field(description="Phone, email, or handle to sign up")


class Extraction(BaseModel):
    """Claude's verdict on one RawPost."""

    is_cooking_class_post: bool = Field(
        description="True only if the post advertises a class/workshop people can attend"
    )
    reason: str = Field(description="One short sentence explaining the verdict")
    classes: list[CookingClass]


def _norm(s: Optional[str]) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def class_key(c: CookingClass) -> str:
    """Stable id used to dedupe the same class seen on several platforms."""
    basis = "|".join([_norm(c.title), c.start_date or "", _norm(c.town), _norm(c.host)])
    return hashlib.sha1(basis.encode()).hexdigest()[:16]
