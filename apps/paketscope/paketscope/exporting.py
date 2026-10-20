"""Helpers for safer plain-text exports."""
from __future__ import annotations

from typing import Any


def csv_safe_value(value: Any) -> str:
    """Prevent spreadsheet software from interpreting exported cells as formulas."""
    text = str(value if value is not None else "")
    significant = text.lstrip(" \t\r\n")
    if significant.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def csv_safe_record(record: dict[str, Any]) -> dict[str, str]:
    return {str(key): csv_safe_value(value) for key, value in record.items()}
