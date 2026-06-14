"""Ранжирование похожих гонок по venue/ветру/дистанции/классу. stdlib.

Источник — словарь `races` из VAULT/sailing/.race-index.json (кэш заголовков,
который заполняют /sail-race и /sail-weather).
"""
from typing import Optional

_CARD_ORDER = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
_BUCKETS = ["0-5", "5-10", "10-15", "15-20", "20+"]


def _card_match(a: Optional[str], b: Optional[str]) -> int:
    """2 — тот же румб, 1 — соседний, иначе 0."""
    if not a or not b:
        return 0
    if a == b:
        return 2
    if a in _CARD_ORDER and b in _CARD_ORDER:
        i, j = _CARD_ORDER.index(a), _CARD_ORDER.index(b)
        if min((i - j) % 8, (j - i) % 8) == 1:
            return 1
    return 0


def _bucket_match(a: Optional[str], b: Optional[str]) -> int:
    """2 — тот же бакет, 1 — соседний, иначе 0."""
    if not a or not b:
        return 0
    if a == b:
        return 2
    if a in _BUCKETS and b in _BUCKETS and abs(_BUCKETS.index(a) - _BUCKETS.index(b)) == 1:
        return 1
    return 0


def score(query: dict, race: dict) -> int:
    s = 0
    if query.get("venue") and race.get("venue") == query["venue"]:
        s += 3
    s += _card_match(query.get("wind_dir_card"), race.get("wind_dir_card"))
    s += _bucket_match(query.get("wind_bucket"), race.get("wind_bucket"))
    if query.get("course_type") and race.get("course_type") == query["course_type"]:
        s += 1
    if query.get("class") and race.get("class") == query["class"]:
        s += 1
    q_d, r_d = query.get("distance_nm"), race.get("distance_nm")
    if q_d and r_d and abs(q_d - r_d) <= max(0.5, 0.2 * q_d):
        s += 1
    return s


def find_similar(index: dict, query: dict, exclude: Optional[str] = None,
                 min_score: int = 3, limit: int = 10):
    races = (index or {}).get("races", {})
    out = []
    for slug, r in races.items():
        if slug == exclude:
            continue
        sc = score(query, r)
        if sc >= min_score:
            out.append({"slug": slug, "score": sc, **r})
    return sorted(out, key=lambda x: (-x["score"], x.get("date", "")))[:limit]
