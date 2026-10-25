#!/usr/bin/env python3
"""Apply the small, reviewed Sorot maintenance overlay to the verified 0.5.0 source ZIP."""
from __future__ import annotations

import sys
from pathlib import Path

NEW_RUN_AND_TERMINATE = r'''def _run(
    args: list[str],
    *,
    timeout: float,
    cancel: CancelToken | None,
    binary: bool = False,
    max_output_bytes: int = MAX_COMMAND_OUTPUT_BYTES,
) -> bytes:
    """Run rclone with time, cancellation, and output bounds.

    stdout is accumulated only up to max_output_bytes; stderr keeps only its
    final 16 KiB. This prevents large remote listings or a broken executable
    from exhausting the application's memory while its pipes are drained.
    """
    if not isinstance(max_output_bytes, int) or isinstance(max_output_bytes, bool):
        raise ValueError("max_output_bytes must be an integer")
    if not 1 <= max_output_bytes <= MAX_TEXT_BYTES + 1:
        raise ValueError(f"max_output_bytes must be between 1 and {MAX_TEXT_BYTES + 1}")
    if cancel is not None and cancel.cancelled:
        raise OperationCancelled()

    executable = _require_rclone()
    command = [executable, *args]
    LOGGER.info("Menjalankan rclone: subperintah=%s", args[0] if args else "")
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            bufsize=0,
        )
    except OSError as exc:
        raise DriveIntegrationError(f"rclone tidak dapat dijalankan: {exc.strerror or exc}") from exc

    assert process.stdout is not None and process.stderr is not None
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, ("stdout", process.stdout))
    selector.register(process.stderr, selectors.EVENT_READ, ("stderr", process.stderr))
    stdout_chunks: list[bytes] = []
    stdout_size = 0
    stderr_tail = bytearray()
    deadline = time.monotonic() + max(0.0, timeout)

    try:
        while selector.get_map() or process.poll() is None:
            if cancel is not None and cancel.cancelled:
                raise OperationCancelled()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise DriveIntegrationError(
                    "Operasi Drive melewati batas waktu. Periksa koneksi internet dan konfigurasi rclone."
                )
            if not selector.get_map():
                time.sleep(min(_POLL_SECONDS, remaining))
                continue

            for key, _ in selector.select(timeout=min(_POLL_SECONDS, remaining)):
                stream_role, stream = key.data
                chunk = os.read(stream.fileno(), 65_536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    stream.close()
                    continue
                if stream_role == "stdout":
                    stdout_size += len(chunk)
                    if stdout_size > max_output_bytes:
                        raise DriveIntegrationError(
                            f"Keluaran rclone terlalu besar (batas {max_output_bytes / 1_000_000:.1f} MB). "
                            "Batasi folder atau gunakan berkas yang lebih kecil."
                        )
                    stdout_chunks.append(chunk)
                else:
                    stderr_tail.extend(chunk)
                    if len(stderr_tail) > MAX_STDERR_CAPTURE_BYTES:
                        del stderr_tail[:-MAX_STDERR_CAPTURE_BYTES]
    except BaseException:
        if process.poll() is None:
            _terminate(process)
        raise
    finally:
        selector.close()
        for stream in (process.stdout, process.stderr):
            if not stream.closed:
                stream.close()

    if process.returncode != 0:
        message = stderr_tail.decode("utf-8", errors="replace").strip().splitlines()
        detail = message[-1] if message else f"kode keluar {process.returncode}"
        raise DriveIntegrationError(f"rclone gagal: {detail}")
    return b"".join(stdout_chunks)


def _terminate(process: subprocess.Popen) -> None:
    """Kill a child without buffering potentially unbounded remaining output."""
    try:
        process.kill()
    except OSError:
        pass
    for stream in (process.stdout, process.stderr):
        if stream is not None and not stream.closed:
            try:
                stream.close()
            except OSError:
                pass
    try:
        process.wait(timeout=5)
    except Exception:  # noqa: BLE001 - best-effort cleanup
        pass
'''


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one match for {label}; found {count}.")
    return text.replace(old, new, 1)


def apply(root: Path) -> None:
    drive_path = root / "src/sorot/services/drive_service.py"
    source = drive_path.read_text(encoding="utf-8")
    if "MAX_COMMAND_OUTPUT_BYTES = 1_000_000" in source:
        raise RuntimeError("The Sorot maintenance overlay is already applied.")
    source = replace_once(source, "import logging\n", "import logging\nimport os\n", "drive os import")
    source = replace_once(source, "import re\n", "import re\nimport selectors\n", "drive selectors import")
    source = replace_once(
        source,
        "MAX_TEXT_BYTES = 5_000_000\n",
        "MAX_TEXT_BYTES = 5_000_000\nMAX_COMMAND_OUTPUT_BYTES = 1_000_000\nMAX_STDERR_CAPTURE_BYTES = 16_000\n",
        "drive output bounds",
    )
    start = source.index("def _run(args: list[str]")
    end = source.index("\ndef validate_remote(", start)
    source = source[:start] + NEW_RUN_AND_TERMINATE + "\n\n" + source[end + 1:]
    source = replace_once(
        source,
        '        timeout=60,\n        cancel=cancel,\n    )\n    files = [line.strip()',
        '        timeout=60,\n        cancel=cancel,\n        max_output_bytes=MAX_TEXT_BYTES,\n    )\n    files = [line.strip()',
        "bounded remote listing",
    )
    source = replace_once(
        source,
        '    out = _run(["cat", target, "--count", str(MAX_TEXT_BYTES + 1), *_RCLONE_LIMITS], timeout=60, cancel=cancel)\n',
        '    out = _run(\n        ["cat", target, "--count", str(MAX_TEXT_BYTES + 1), *_RCLONE_LIMITS],\n        timeout=60,\n        cancel=cancel,\n        max_output_bytes=MAX_TEXT_BYTES + 1,\n    )\n',
        "bounded remote file read",
    )
    drive_path.write_text(source, encoding="utf-8")

    fake_path = root / "tests/fake_rclone.py"
    fake = fake_path.read_text(encoding="utf-8")
    fake_version = '    elif cmd == "version":\n        sys.stdout.write("rclone v1.99.0-fake\\\\n- os/arch: linux/amd64\\\\n")'
    fake_version_new = (
        '    elif cmd == "version":\n'
        '        output_size = int(os.environ.get("FAKE_RCLONE_OUTPUT_SIZE", "0"))\n'
        '        if output_size:\n'
        '            sys.stdout.write("x" * output_size)\n'
        '        sys.stdout.write("rclone v1.99.0-fake\\\\n- os/arch: linux/amd64\\\\n")'
    )
    fake_path.write_text(
        replace_once(fake, fake_version, fake_version_new, "fake rclone output switch"),
        encoding="utf-8",
    )

    tests_path = root / "tests/test_drive_service.py"
    tests = tests_path.read_text(encoding="utf-8")
    marker = "def test_run_can_be_cancelled(fake, monkeypatch):\n"
    tests_added = (
        "def test_run_rejects_large_stdout_without_buffering_unbounded_output(fake, monkeypatch):\n"
        '    monkeypatch.setenv("FAKE_RCLONE_OUTPUT_SIZE", "2000000")\n'
        '    with pytest.raises(DriveIntegrationError, match="Keluaran rclone terlalu besar"):\n'
        '        drive._run(["version"], timeout=5, cancel=None, max_output_bytes=1024)\n'
        "\n\n"
        "def test_run_rejects_invalid_output_limit(fake):\n"
        '    with pytest.raises(ValueError, match="max_output_bytes"):\n'
        '        drive._run(["version"], timeout=5, cancel=None, max_output_bytes=0)\n'
        "\n\n"
    )
    tests_path.write_text(replace_once(tests, marker, tests_added + marker, "drive output bound tests"), encoding="utf-8")

    security_path = root / "SECURITY.md"
    security = security_path.read_text(encoding="utf-8")
    security = replace_once(
        security,
        "Hanya rilis beta terbaru (0.4.x).",
        "Hanya seri beta terbaru yang dipublikasikan dan masih didukung (saat ini 0.5.x Beta). Rilis beta belum mendapat jaminan dukungan produksi.",
        "supported beta version",
    )
    security = replace_once(
        security,
        "Kontak keamanan maintainer **belum ditetapkan** (repositori belum dipublikasikan). Setelah repositori publik dibuat, gunakan fitur *Private vulnerability reporting* GitHub dan perbarui berkas ini dengan kontak yang valid. Jangan membuka isu publik untuk kerentanan.",
        "Untuk melaporkan kerentanan keamanan atau masalah keamanan serius yang berkaitan langsung dengan Sorot, kirim email ke **muhammadandreatama@outlook.com** dengan subjek **[Sorot Security] Laporan Kerentanan**. Gunakan alamat ini hanya untuk laporan keamanan dan urusan penting yang terkait langsung dengan Sorot; jangan kirim promosi, spam, atau pesan yang tidak berkaitan. Jangan membuka isu publik berisi detail yang dapat dieksploitasi. Sertakan versi Sorot, distro/lingkungan desktop, langkah reproduksi, dan dampak yang diamati; jangan sertakan kata sandi, token API, atau data sensitif.",
        "security reporting guidance",
    )
    security_path.write_text(security, encoding="utf-8")

    # The original beta artifacts remain immutable. Apply maintainer details only
    # to the temporary source tree used by CI and the next intentional build.
    contact = "Muhammad Andreatama <muhammadandreatama@outlook.com>"

    control_path = root / "packaging/control.in"
    control = control_path.read_text(encoding="utf-8")
    control_path.write_text(
        replace_once(
            control,
            "Maintainer: Muhammad Andreatama <maintainer@sorot.invalid>",
            f"Maintainer: {contact}",
            "Debian maintainer email",
        ),
        encoding="utf-8",
    )

    changelog_path = root / "packaging/debian-changelog"
    changelog = changelog_path.read_text(encoding="utf-8")
    changelog_path.write_text(
        replace_once(
            changelog,
            " -- Muhammad Andreatama <maintainer@sorot.invalid>  Sun, 18 Oct 2026 00:00:00 +0000",
            f" -- {contact}  Sun, 18 Oct 2026 00:00:00 +0000",
            "Debian changelog maintainer email",
        ),
        encoding="utf-8",
    )

    copyright_path = root / "packaging/copyright"
    copyright_text = copyright_path.read_text(encoding="utf-8")
    copyright_path.write_text(
        replace_once(
            copyright_text,
            "Upstream-Name: Sorot\nSource: (belum ada URL repositori publik)",
            "Upstream-Name: Sorot\nUpstream-Contact: " + contact + "\nSource: https://github.com/M-TamDre07/Linux-Software-Lab/tree/main/apps/sorot",
            "Debian copyright upstream contact and source URL",
        ),
        encoding="utf-8",
    )

    checklist_path = root / "docs/RELEASE-CHECKLIST.md"
    checklist = checklist_path.read_text(encoding="utf-8")
    checklist_path.write_text(
        replace_once(
            checklist,
            "- [ ] Ganti maintainer placeholder `maintainer@sorot.invalid` (nama sudah Muhammad Andreatama; **email asli belum ada**) di `packaging/control.in`, `packaging/debian-changelog`, `packaging/copyright` dengan kontak nyata",
            "- [x] Kontak maintainer publik telah diberikan; overlay mengisi `packaging/control.in`, `packaging/debian-changelog`, `packaging/copyright`, dan `SECURITY.md` untuk build berikutnya. Artefak beta 0.5.0 yang ada tetap tidak berubah.",
            "release checklist maintainer contact",
        ),
        encoding="utf-8",
    )


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: apply.py SOURCE_ROOT", file=sys.stderr)
        return 2
    root = Path(sys.argv[1]).resolve()
    required = [root / "src/sorot/services/drive_service.py", root / "tests/test_drive_service.py", root / "SECURITY.md"]
    if not all(path.is_file() for path in required):
        print("Source root does not look like the verified Sorot 0.5.0 source archive.", file=sys.stderr)
        return 2
    try:
        apply(root)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Sorot maintenance overlay failed: {exc}", file=sys.stderr)
        return 1
    print("Applied Sorot maintenance overlay: bounded rclone output, regression tests, maintainer metadata, and current security policy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
