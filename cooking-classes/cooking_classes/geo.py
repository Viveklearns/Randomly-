"""Bergen County, NJ geography used to double-check Claude's location calls."""

from __future__ import annotations

import re
from typing import Optional

# All 70 municipalities in Bergen County, NJ.
BERGEN_MUNICIPALITIES = [
    "Allendale", "Alpine", "Bergenfield", "Bogota", "Carlstadt", "Cliffside Park",
    "Closter", "Cresskill", "Demarest", "Dumont", "East Rutherford", "Edgewater",
    "Elmwood Park", "Emerson", "Englewood", "Englewood Cliffs", "Fair Lawn", "Fairview",
    "Fort Lee", "Franklin Lakes", "Garfield", "Glen Rock", "Hackensack", "Harrington Park",
    "Hasbrouck Heights", "Haworth", "Hillsdale", "Ho-Ho-Kus", "Leonia", "Little Ferry",
    "Lodi", "Lyndhurst", "Mahwah", "Maywood", "Midland Park", "Montvale", "Moonachie",
    "New Milford", "North Arlington", "Northvale", "Norwood", "Oakland", "Old Tappan",
    "Oradell", "Palisades Park", "Paramus", "Park Ridge", "Ramsey", "Ridgefield",
    "Ridgefield Park", "Ridgewood", "River Edge", "River Vale", "Rochelle Park",
    "Rockleigh", "Rutherford", "Saddle Brook", "Saddle River", "South Hackensack",
    "Teaneck", "Tenafly", "Teterboro", "Upper Saddle River", "Waldwick", "Wallington",
    "Washington Township", "Westwood", "Wood-Ridge", "Woodcliff Lake", "Wyckoff",
]

_NORMALIZED = {re.sub(r"[^a-z]", "", t.lower()): t for t in BERGEN_MUNICIPALITIES}


def canonical_town(town: Optional[str]) -> Optional[str]:
    """'ho ho kus' / 'Hohokus' / 'Fair Lawn, NJ' -> canonical name, else None."""
    if not town:
        return None
    head = town.split(",")[0]
    head = re.sub(r"\btwp\b\.?", "township", head, flags=re.I)
    key = re.sub(r"[^a-z]", "", head.lower())
    if key in _NORMALIZED:
        return _NORMALIZED[key]
    stripped = re.sub(r"\b(nj|new jersey|township|borough|city|of)\b", "", head, flags=re.I)
    return _NORMALIZED.get(re.sub(r"[^a-z]", "", stripped.lower()))


def mentions_bergen(text: str) -> bool:
    """Cheap pre-filter: does the text name Bergen County or one of its towns?"""
    if re.search(r"\bbergen\b", text, re.I):
        return True
    return any(re.search(rf"\b{re.escape(t)}\b", text, re.I) for t in BERGEN_MUNICIPALITIES)
