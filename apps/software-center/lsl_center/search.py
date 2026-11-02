"""Shared offline search semantics for the desktop launcher and CLI."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from difflib import SequenceMatcher

from .models import Application

FIELD_ALIASES = {
    "nama": "name",
    "name": "name",
    "id": "id",
    "tag": "tags",
    "tags": "tags",
    "label": "tags",
    "kategori": "category",
    "category": "category",
    "platform": "platforms",
    "distro": "platforms",
    "os": "platforms",
    "status": "status",
    "versi": "version",
    "version": "version",
    "jenis": "type",
    "type": "type",
    "fitur": "features",
    "feature": "features",
    "features": "features",
}

SYNONYMS = {
    "paket": ("package", "apt", "dpkg", "software", "aplikasi"),
    "package": ("paket", "apt", "dpkg", "software"),
    "instalasi": ("install", "installer", "pemasangan", "pasang"),
    "install": ("instalasi", "installer", "pemasangan", "pasang"),
    "installer": ("instalasi", "install", "pemasangan"),
    "pembaruan": ("update", "upgrade", "perbarui"),
    "update": ("pembaruan", "upgrade", "perbarui"),
    "upgrade": ("pembaruan", "update", "perbarui"),
    "inventaris": ("inventory", "daftar aplikasi", "paket"),
    "inventory": ("inventaris", "daftar aplikasi"),
    "teleprompter": ("prompter", "naskah", "presentasi", "gulir teks"),
    "telepromter": ("teleprompter", "prompter", "naskah"),
    "prompter": ("teleprompter", "naskah", "presentasi"),
    "mirror": ("cermin", "flip", "balik"),
    "cermin": ("mirror", "flip", "balik"),
    "jaringan": ("network", "wifi", "wi-fi"),
    "network": ("jaringan", "wifi", "wi-fi"),
    "desain": ("design", "poster", "grafis"),
    "design": ("desain", "poster", "grafis"),
    "cadangan": ("backup", "restore", "pemulihan"),
    "backup": ("cadangan", "restore", "pemulihan"),
    "keamanan": ("security", "privasi", "permission"),
    "security": ("keamanan", "privasi", "permission"),
}

QUERY_PARTS = re.compile(r'-?[^\\s"]+:"[^"]*"|"[^"]*"|[^\\s]+')
WORD_PARTS = re.compile(r"[^a-z0-9.+-]+")


def normalise(value: object) -> str:
    """Normalize accents and case consistently across Indonesian/English text."""
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return text.casefold().strip()


def _words(value: object) -> tuple[str, ...]:
    return tuple(part for part in WORD_PARTS.split(normalise(value)) if part)


def parse_query(query: str) -> tuple[tuple[str, str, bool], ...]:
    """Parse quoted phrases, field-qualified terms, and negative terms."""
    parsed: list[tuple[str, str, bool]] = []
    for part in QUERY_PARTS.findall(str(query or "")):
        negative = part.startswith("-")
        token = part[1:] if negative else part
        field = "all"
        if ":" in token:
            possible_field, remainder = token.split(":", 1)
            resolved = FIELD_ALIASES.get(normalise(possible_field))
            if resolved:
                field = resolved
                token = remainder
        value = normalise(token.strip('"'))
        if value:
            parsed.append((field, value, negative))
    return tuple(parsed)


def _field_values(app: Application) -> dict[str, str]:
    return {
        "id": normalise(app.id),
        "name": normalise(app.name),
        "summary": normalise(app.summary),
        "description": normalise(app.description),
        "category": normalise(app.category),
        "tags": normalise(" ".join((*app.tags, *app.keywords))),
        "features": normalise(" ".join(app.features)),
        "platforms": normalise(" ".join(app.platforms)),
        "status": normalise(app.status),
        "version": normalise(app.version),
        "type": normalise(app.app_type),
    }


def _term_quality(term: str, value: str) -> float:
    if not value:
        return 0.0
    if term in value:
        return 1.0
    words = _words(value)
    if any(word.startswith(term) for word in words if len(term) >= 3):
        return 0.82
    if len(term) < 5:
        return 0.0
    threshold = 0.82 if len(term) < 8 else 0.76
    best = max(
        (
            SequenceMatcher(None, term, word).ratio()
            for word in words
            if abs(len(word) - len(term)) <= 2
        ),
        default=0.0,
    )
    return best if best >= threshold else 0.0


def _expanded_terms(term: str) -> tuple[str, ...]:
    return (term, *(normalise(alias) for alias in SYNONYMS.get(term, ())))


def _score_term(fields: dict[str, str], field: str, term: str) -> float:
    weights = {
        "id": 95,
        "name": 90,
        "tags": 45,
        "features": 35,
        "category": 28,
        "summary": 20,
        "platforms": 16,
        "version": 12,
        "status": 10,
        "type": 8,
        "description": 5,
    }
    candidates = fields.items() if field == "all" else ((field, fields.get(field, "")),)
    return max(
        (_term_quality(term, value) * weights.get(key, 1) for key, value in candidates),
        default=0.0,
    )


def score_application(app: Application, query: str) -> float | None:
    """Return relevance score, or None when the application does not match."""
    terms = parse_query(query)
    if not terms:
        return 0.0
    fields = _field_values(app)
    total = 0.0
    for field, term, negative in terms:
        score = max(
            (_score_term(fields, field, candidate) for candidate in _expanded_terms(term)),
            default=0.0,
        )
        if negative:
            if score > 0:
                return None
            continue
        if score <= 0:
            return None
        total += score
    return total


def search_applications(
    applications: Iterable[Application],
    query: str,
) -> tuple[Application, ...]:
    """Return all matches ordered by relevance, then localized application name."""
    scored = [
        (score, app)
        for app in applications
        if (score := score_application(app, query)) is not None
    ]
    scored.sort(key=lambda item: (-item[0], normalise(item[1].name), item[1].id))
    return tuple(app for _score, app in scored)
