"""Bounded local system inspection and opt-in polkit metadata inspection."""
from __future__ import annotations

import json
import os
import platform
import shutil
import stat
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MAX_ADMIN_OUTPUT = 2 * 1024 * 1024
TRUSTED_HELPER = Path("/usr/lib/python3/dist-packages/paketscope/admin_helper.py")


def _read_os_release() -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        for line in Path("/etc/os-release").read_text(encoding="utf-8", errors="replace").splitlines():
            key, sep, value = line.partition("=")
            if not sep or key not in {"NAME", "ID", "ID_LIKE", "VERSION_ID", "PRETTY_NAME"}:
                continue
            values[key] = value.strip().strip('"').strip("'")
    except OSError:
        values["PRETTY_NAME"] = "Tidak dapat membaca /etc/os-release"
    return values


def _read_memory() -> dict[str, int]:
    values: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="ascii", errors="replace").splitlines():
            key, _, rest = line.partition(":")
            if key not in {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}:
                continue
            number = rest.strip().split()[0]
            values[key] = int(number) // 1024
    except (OSError, ValueError, IndexError):
        pass
    return values


def _cpu_summary() -> dict[str, Any]:
    result: dict[str, Any] = {
        "logical_processors": os.cpu_count() or 0,
        "architecture": platform.machine() or "unknown",
        "model": "Tidak tersedia",
    }
    try:
        for line in Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace").splitlines():
            key, sep, value = line.partition(":")
            if sep and key.strip() in {"model name", "Hardware", "Processor"}:
                result["model"] = value.strip()[:180]
                break
    except OSError:
        pass
    return result


def _directory_overview(path: Path, cap: int = 80) -> dict[str, Any]:
    try:
        with os.scandir(path) as iterator:
            entries = sorted(iterator, key=lambda entry: entry.name.casefold())
        names = [entry.name for entry in entries[:cap]]
        truncated = len(entries) > cap
        return {"path": str(path), "entries": names, "truncated": truncated}
    except OSError as exc:
        return {"path": str(path), "entries": [], "error": exc.strerror or "Tidak dapat dibaca"}


def _disk_overview(paths: tuple[Path, ...]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in paths:
        try:
            resolved = str(path.resolve(strict=True))
            if resolved in seen:
                continue
            seen.add(resolved)
            usage = shutil.disk_usage(path)
        except (OSError, RuntimeError):
            continue
        output.append({
            "path": str(path),
            "total_gib": round(usage.total / (1024 ** 3), 2),
            "used_gib": round(usage.used / (1024 ** 3), 2),
            "free_gib": round(usage.free / (1024 ** 3), 2),
            "used_percent": round((usage.used / usage.total) * 100, 1) if usage.total else 0.0,
        })
    return output


def collect_system_snapshot() -> dict[str, Any]:
    """Collect an unprivileged snapshot; no commands or files are modified."""
    uname = platform.uname()
    module_count = 0
    module_names: list[str] = []
    try:
        for line in Path("/proc/modules").read_text(encoding="utf-8", errors="replace").splitlines():
            name = line.split(maxsplit=1)[0] if line.strip() else ""
            if name:
                module_count += 1
                if len(module_names) < 40:
                    module_names.append(name)
    except OSError:
        pass

    overview_paths = (Path("/"), Path("/etc"), Path("/usr"), Path("/var"), Path("/opt"), Path("/boot"), Path("/home"))
    existing_directories = tuple(path for path in overview_paths if path.is_dir())
    disks = _disk_overview((Path("/"), Path("/home"), Path("/boot")))

    try:
        load_average = [round(float(value), 2) for value in os.getloadavg()]
    except (AttributeError, OSError):
        load_average = []

    return {
        "schema_version": 1,
        "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "read-only / user",
        "operating_system": _read_os_release(),
        "kernel": {"system": uname.system, "release": uname.release, "version": uname.version[:220]},
        "machine": {"architecture": uname.machine, "hostname": uname.node, "python": platform.python_version()},
        "cpu": _cpu_summary(),
        "memory_mib": _read_memory(),
        "disk_usage": disks,
        "load_average_1_5_15": load_average,
        "kernel_modules": {"count": module_count, "sample": module_names},
        "filesystem_layout": [_directory_overview(path) for path in existing_directories],
        "notice": "Snapshot lokal hanya-baca. Tidak ada file atau konfigurasi yang diubah; data tidak dikirim ke jaringan.",
    }


def run_privileged_metadata_inspection() -> dict[str, Any]:
    """Run the fixed, read-only helper after explicit app opt-in and polkit auth."""
    try:
        helper = TRUSTED_HELPER.resolve(strict=True)
        info = helper.stat()
    except OSError as exc:
        raise RuntimeError(
            "Inspeksi administrator hanya tersedia dari paket Debian terpasang yang tepercaya. "
            "Mode source/virtualenv tidak menaikkan hak akses."
        ) from exc
    if helper != TRUSTED_HELPER or not stat.S_ISREG(info.st_mode):
        raise RuntimeError("Helper administrator tidak berada pada lokasi paket sistem yang diizinkan.")
    if info.st_uid != 0 or info.st_mode & 0o022:
        raise RuntimeError("Helper administrator tidak tepercaya: pemilik harus root dan file tidak boleh writable oleh group/others.")
    for directory in (helper.parent, helper.parent.parent, helper.parent.parent.parent, helper.parent.parent.parent.parent):
        try:
            directory_info = directory.stat()
        except OSError as exc:
            raise RuntimeError("Direktori paket sistem tidak dapat diverifikasi.") from exc
        if directory_info.st_uid != 0 or directory_info.st_mode & 0o022:
            raise RuntimeError("Direktori helper administrator tidak aman untuk dijalankan sebagai root.")

    executable = Path("/usr/bin/pkexec")
    python = Path("/usr/bin/python3")
    if not executable.is_file() or not python.is_file():
        raise RuntimeError("pkexec atau /usr/bin/python3 tidak tersedia.")
    argv = [str(executable), str(python), "-I", str(helper), "--metadata"]
    try:
        completed = subprocess.run(
            argv, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=45, check=False, shell=False,
            env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Inspeksi administrator melewati batas waktu 45 detik.") from exc
    if completed.returncode != 0:
        if completed.returncode == 126:
            raise RuntimeError("Permintaan izin dibatalkan atau ditolak melalui Polkit.")
        detail = completed.stderr.strip()[-300:]
        raise RuntimeError("Inspeksi administrator gagal melalui Polkit." + (f" Detail: {detail}" if detail else ""))
    if len(completed.stdout.encode("utf-8", errors="replace")) > MAX_ADMIN_OUTPUT:
        raise RuntimeError("Hasil inspeksi melewati batas ukuran yang diizinkan.")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Helper administrator mengembalikan hasil yang tidak valid.") from exc
    return validate_admin_payload(payload)


def validate_admin_payload(payload: object) -> dict[str, Any]:
    """Validate helper output before it is shown in the GUI."""
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise RuntimeError("Versi format inspeksi administrator tidak dikenal.")
    entries = payload.get("entries")
    if not isinstance(entries, list) or len(entries) > 3000:
        raise RuntimeError("Daftar metadata administrator tidak valid.")
    allowed_roots = ("/etc", "/boot", "/usr/local", "/opt")
    normalized: list[dict[str, Any]] = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        if not isinstance(path, str) or not any(path == root or path.startswith(root + "/") for root in allowed_roots):
            continue
        try:
            owner_uid = int(item.get("owner_uid", -1))
            group_gid = int(item.get("group_gid", -1))
            size_bytes = max(0, int(item.get("size_bytes", 0)))
        except (TypeError, ValueError):
            continue
        normalized.append({
            "path": path[:512],
            "type": str(item.get("type", "unknown"))[:24],
            "mode": str(item.get("mode", ""))[:12],
            "owner_uid": owner_uid,
            "group_gid": group_gid,
            "size_bytes": size_bytes,
        })
    return {
        "schema_version": 1,
        "collected_at": str(payload.get("collected_at", ""))[:64],
        "scope": "metadata-only",
        "entries": normalized,
        "diagnostics": [str(item)[:300] for item in payload.get("diagnostics", [])[:100]]
        if isinstance(payload.get("diagnostics", []), list) else [],
        "notice": "Metadata sistem saja: path, tipe, izin, UID/GID, ukuran. Isi file, kredensial, dan private key tidak dibaca.",
    }
