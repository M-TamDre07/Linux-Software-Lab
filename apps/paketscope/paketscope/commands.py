"""Small wrappers for read-only OS commands. Never invoke a shell or sudo."""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CommandResult:
    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


class CommandUnavailable(RuntimeError):
    pass


class CommandTimedOut(RuntimeError):
    pass


def run_command(argv: list[str], timeout: float = 20.0) -> CommandResult:
    if not argv or not argv[0]:
        raise ValueError("Perintah kosong tidak diizinkan.")
    executable = shutil.which(argv[0])
    if executable is None:
        raise CommandUnavailable(f"Perintah {argv[0]} tidak ditemukan.")
    safe_argv = [executable, *argv[1:]]
    try:
        completed = subprocess.run(
            safe_argv,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=False,
            env={**os.environ, "LC_ALL": "C"},
        )
    except subprocess.TimeoutExpired as exc:
        raise CommandTimedOut(f"{argv[0]} melewati batas waktu {timeout:g} detik.") from exc
    return CommandResult(
        argv=tuple(argv),
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
