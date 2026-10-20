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


import os
import tempfile
from pathlib import Path


def write_private_file(path: str | Path, data: bytes) -> None:
    """Atomically replace a user-selected file with owner-only permissions."""
    destination = Path(path)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix="." + destination.name + ".",
        suffix=".tmp",
        dir=str(destination.parent),
    )
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, destination)
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise
