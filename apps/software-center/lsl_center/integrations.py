"""Reviewed local app integrations; remote catalog metadata never provides commands."""

from __future__ import annotations

import collections.abc
import dataclasses
import re
import shutil


_APPLICATION_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclasses.dataclass(frozen=True, slots=True)
class LocalApplicationIntegration:
    """A small, code-reviewed bridge from a catalog ID to local executable names."""

    application_id: str
    executable_candidates: tuple[str, ...]


# Keep executable names in reviewed application code, never in GitHub JSON.
# A tuple prevents callers from changing the registry at runtime.
LOCAL_INTEGRATIONS: tuple[LocalApplicationIntegration, ...] = (
    LocalApplicationIntegration(
        application_id="paketscope",
        executable_candidates=("paketscope",),
    ),
    LocalApplicationIntegration(
        application_id="sorot",
        executable_candidates=("sorot",),
    ),
)


def integration_for(application_id: str) -> LocalApplicationIntegration | None:
    """Return a reviewed integration for a valid catalog ID, if one exists."""
    if not isinstance(application_id, str):
        return None
    normalized = application_id.casefold()
    if not _APPLICATION_ID.fullmatch(normalized):
        return None
    return next(
        (item for item in LOCAL_INTEGRATIONS if item.application_id == normalized),
        None,
    )


def executable_for(
    application_id: str,
    which: collections.abc.Callable[[str], str | None] | None = None,
) -> str | None:
    """Resolve only executable candidates registered in trusted local code."""
    integration = integration_for(application_id)
    if integration is None:
        return None

    lookup = which or shutil.which
    for command in integration.executable_candidates:
        path = lookup(command)
        if path:
            return path
    return None
