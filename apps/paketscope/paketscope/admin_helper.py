"""Privileged, fixed-scope metadata collector for PaketScope.

This helper is called only through pkexec after an explicit user action. It is
not a shell, does not accept user-provided paths, never reads file contents,
and refuses to run unless installed in the root-owned Debian package path.
"""
from __future__ import annotations

import json
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

TRUSTED_FILE = Path("/usr/lib/python3/dist-packages/paketscope/admin_helper.py")
ALLOWED_ROOTS = (Path("/etc"), Path("/boot"), Path("/usr/local"), Path("/opt"))
EXCLUDED_DIRECTORY_NAMES = frozenset({
    "private", "ssh", "sudoers.d", "system-connections", "auth.conf.d",
})
EXCLUDED_FILE_NAMES = frozenset({
    "shadow", "shadow-", "gshadow", "gshadow-", "master.passwd",
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", "authorized_keys",
    "auth.conf", "credentials", "netrc",
})
EXCLUDED_SUFFIXES = frozenset({".pem", ".key", ".p12", ".pfx", ".keystore"})


def _require_trusted_root_install() -> None:
    if os.geteuid() != 0:
        raise PermissionError("Helper must be started by a trusted polkit authorization.")
    resolved = Path(__file__).resolve(strict=True)
    if resolved != TRUSTED_FILE:
        raise PermissionError("Helper is not from the trusted installed PaketScope package.")
    current = resolved
    while True:
        info = current.stat()
        if info.st_uid != 0 or info.st_mode & 0o022:
            raise PermissionError("Helper/package path must be root-owned and not writable by group or others.")
        if current == Path("/usr"):
            break
        parent = current.parent
        if parent == current or not parent.is_relative_to(Path("/usr")):
            raise PermissionError("Helper path is outside the system package location.")
        current = parent


def _excluded(path: Path) -> bool:
    if path.name.casefold() in EXCLUDED_FILE_NAMES:
        return True
    if path.suffix.casefold() in EXCLUDED_SUFFIXES:
        return True
    return path.name.startswith(".env")


def _entry(path: Path) -> dict[str, object] | None:
    try:
        info = path.lstat()
    except OSError:
        return None
    if stat.S_ISLNK(info.st_mode):
        return None
    if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
        return None
    if _excluded(path):
        return None
    kind = "directory" if stat.S_ISDIR(info.st_mode) else "file"
    return {
        "path": str(path),
        "type": kind,
        "mode": stat.filemode(info.st_mode),
        "owner_uid": info.st_uid,
        "group_gid": info.st_gid,
        "size_bytes": info.st_size if kind == "file" else 0,
    }


def collect_metadata() -> dict[str, object]:
    entries: list[dict[str, object]] = []
    diagnostics: list[str] = []
    max_entries = 3000
    # This fixed allowlist and depth limit are part of the security boundary.
    for root in ALLOWED_ROOTS:
        try:
            root_info = root.lstat()
        except OSError:
            continue
        if stat.S_ISLNK(root_info.st_mode) or not stat.S_ISDIR(root_info.st_mode):
            continue
        root_entry = _entry(root)
        if root_entry:
            entries.append(root_entry)
        current_level: list[Path] = [root]
        for _depth in range(2):
            next_level: list[Path] = []
            for directory in current_level:
                try:
                    with os.scandir(directory) as iterator:
                        children = sorted(iterator, key=lambda item: item.name.casefold())
                except OSError as exc:
                    if len(diagnostics) < 100:
                        diagnostics.append(f"{directory}: {exc.strerror or 'tidak dapat dibaca'}")
                    continue
                for child in children:
                    candidate = Path(child.path)
                    if child.is_symlink():
                        continue
                    if candidate.name.casefold() in EXCLUDED_DIRECTORY_NAMES:
                        continue
                    item = _entry(candidate)
                    if item is None:
                        continue
                    entries.append(item)
                    if item["type"] == "directory" and _depth == 0:
                        next_level.append(candidate)
                    if len(entries) >= max_entries:
                        diagnostics.append(f"Batas {max_entries} entri tercapai; sebagian metadata tidak ditampilkan.")
                        break
                if len(entries) >= max_entries:
                    break
            current_level = next_level
            if not current_level or len(entries) >= max_entries:
                break
        if len(entries) >= max_entries:
            break
    return {
        "schema_version": 1,
        "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope": "metadata-only",
        "roots": [str(path) for path in ALLOWED_ROOTS],
        "entries": entries,
        "diagnostics": diagnostics,
    }


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args != ["--metadata"]:
        print("Only the fixed --metadata action is supported.", file=sys.stderr)
        return 2
    try:
        _require_trusted_root_install()
        result = collect_metadata()
    except (OSError, PermissionError, RuntimeError) as exc:
        print(str(exc)[:300], file=sys.stderr)
        return 1
    print(json.dumps(result, separators=(",", ":"), ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
