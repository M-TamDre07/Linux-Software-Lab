"""Privileged, bounded read-only inspection helper for PaketScope.

Only fixed metadata and a user-selected bounded text file can be read. This is
not a shell, accepts no arbitrary commands, writes nothing, and requires the
root-owned Debian package helper path plus a Polkit authorization.
"""
from __future__ import annotations

import json
import os
import stat
import sys
from datetime import datetime, timezone
from itertools import islice
from pathlib import Path

TRUSTED_FILE = Path("/usr/lib/python3/dist-packages/paketscope/admin_helper.py")
ALLOWED_ROOTS = (
    Path("/etc"), Path("/boot"), Path("/usr/local"), Path("/opt"),
    Path("/var/lib/dpkg"), Path("/var/log"), Path("/usr/share"),
    Path("/usr/bin"), Path("/usr/sbin"), Path("/usr/lib"),
)
MAX_TEXT_FILE_BYTES = 256 * 1024
EXCLUDED_DIRECTORY_NAMES = frozenset({
    "private", "ssh", ".ssh", "sudoers.d", "system-connections", "auth.conf.d",
    "credentials", "credstore", "openvpn", "wireguard",
})
EXCLUDED_FILE_NAMES = frozenset({
    "shadow", "shadow-", "gshadow", "gshadow-", "passwd-", "master.passwd",
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", "id_ed25519_sk",
    "authorized_keys", "known_hosts", "auth.conf", "credentials", "netrc",
    "htpasswd", "privatekey", "private_key", "server.key",
})
EXCLUDED_SUFFIXES = frozenset({
    ".pem", ".key", ".p12", ".pfx", ".keystore", ".kdbx", ".gpg", ".pgp", ".age",
})


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
    if any(part.casefold() in EXCLUDED_DIRECTORY_NAMES for part in path.parts):
        return True
    name = path.name.casefold()
    if name in EXCLUDED_FILE_NAMES or name.startswith(".env"):
        return True
    return path.suffix.casefold() in EXCLUDED_SUFFIXES


def _validate_text_file_path(raw_path: str) -> Path:
    """Resolve a selected path without following symlinks or permitting traversal."""
    candidate = Path(raw_path)
    if not candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("Path must be absolute and cannot contain traversal.")
    if not any(candidate != root and candidate.is_relative_to(root) for root in ALLOWED_ROOTS):
        raise ValueError("Path is outside the allowed system directories.")
    if _excluded(candidate):
        raise ValueError("This path appears to contain sensitive material and is not eligible for reading.")

    current = Path(candidate.anchor)
    for part in candidate.parts[1:]:
        current = current / part
        try:
            info = current.lstat()
        except OSError as exc:
            raise ValueError(f"Path cannot be accessed: {exc.strerror or 'not available'}.") from exc
        if stat.S_ISLNK(info.st_mode):
            raise ValueError("Symlinks are not followed by privileged inspection.")
        if current != candidate:
            if not stat.S_ISDIR(info.st_mode):
                raise ValueError("Every parent component must be a directory.")
            if info.st_uid != 0 or info.st_mode & 0o022:
                raise ValueError("Parent directories must be root-owned and not group/other writable.")

    try:
        info = candidate.lstat()
    except OSError as exc:
        raise ValueError(f"File cannot be accessed: {exc.strerror or 'not available'}.") from exc
    if not stat.S_ISREG(info.st_mode):
        raise ValueError("Only regular text files can be read.")
    if info.st_size > MAX_TEXT_FILE_BYTES:
        raise ValueError(f"File exceeds the {MAX_TEXT_FILE_BYTES // 1024} KiB limit.")
    return candidate


def read_text_file(raw_path: str) -> dict[str, object]:
    """Read a selected UTF-8 file without executing or modifying it."""
    path = _validate_text_file_path(raw_path)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(path, flags)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_TEXT_FILE_BYTES:
            raise ValueError("The file changed or exceeded the permitted size.")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            raw = handle.read(MAX_TEXT_FILE_BYTES + 1)
        if len(raw) > MAX_TEXT_FILE_BYTES or b"\x00" in raw[:4096]:
            raise ValueError("Binary or oversized files are not displayed.")
        try:
            content = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("File is not UTF-8 text; its contents will not be displayed.") from exc
    finally:
        os.close(descriptor)
    return {
        "schema_version": 1,
        "scope": "selected-text-file-read-only",
        "path": str(path),
        "size_bytes": len(raw),
        "content": content,
        "notice": "Read-only. No code is executed and the file is not modified. Maximum 256 KiB.",
    }


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
        for depth in range(2):
            next_level: list[Path] = []
            for directory in current_level:
                try:
                    remaining = max(1, max_entries - len(entries) + 1)
                    with os.scandir(directory) as iterator:
                        children = sorted(islice(iterator, remaining), key=lambda item: item.name.casefold())
                except OSError as exc:
                    if len(diagnostics) < 100:
                        diagnostics.append(f"{directory}: {exc.strerror or 'cannot read'}")
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
                    if item["type"] == "directory" and depth == 0:
                        next_level.append(candidate)
                    if len(entries) >= max_entries:
                        diagnostics.append(f"Entry limit {max_entries} reached; some metadata was omitted.")
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
    if args == ["--metadata"]:
        action = "metadata"
    elif len(args) == 2 and args[0] == "--read-text":
        action = "read-text"
    else:
        print("Supported actions: --metadata or --read-text ABSOLUTE_PATH", file=sys.stderr)
        return 2
    try:
        _require_trusted_root_install()
        result = collect_metadata() if action == "metadata" else read_text_file(args[1])
    except (OSError, PermissionError, RuntimeError, ValueError) as exc:
        print(str(exc)[:300], file=sys.stderr)
        return 1
    print(json.dumps(result, separators=(",", ":"), ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
