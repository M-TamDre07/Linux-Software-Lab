"""Reviewed local app integrations; remote catalog metadata never provides commands."""

from __future__ import annotations

import re
import shutil


_APPLICATION_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# Executable names stay in reviewed application code, never in GitHub JSON.
# The immutable tuple means remote catalog edits cannot alter local launch commands.
LOCAL_INTEGRATIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("paketscope", ("paketscope",)),
    ("sorot", ("sorot",)),
)


def integration_for(application_id: str) -> tuple[str, tuple[str, ...]] | None:
    """Return an approved product/executable pair for a valid catalog ID."""
    if not isinstance(application_id, str):
        return None
    normalized = application_id.casefold()
    if not _APPLICATION_ID.fullmatch(normalized):
        return None
    return next(
        (item for item in LOCAL_INTEGRATIONS if item[0] == normalized),
        None,
    )


def executable_for(application_id: str, which=None) -> str | None:
    """Resolve only executable candidates registered in trusted local code."""
    integration = integration_for(application_id)
    if integration is None:
        return None

    _registered_id, executable_candidates = integration
    lookup = which or shutil.which
    for command in executable_candidates:
        path = lookup(command)
        if path:
            return path
    return None
