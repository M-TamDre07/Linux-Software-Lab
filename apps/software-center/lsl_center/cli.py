"""Command-line interface; all operations use the same catalog and installer core."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from collections.abc import Sequence
from importlib.metadata import PackageNotFoundError, version as distribution_version
from pathlib import Path

from .catalog import (
    CATALOG_URL,
    DISTRIBUTION_INDEX_URL,
    OWNER,
    REPOSITORY,
    WEBSITE_ROOT,
    CatalogError,
    CatalogService,
)
from .distro import artifact_compatibility, detect_system_profile, executable_for
from .integrations import LOCAL_INTEGRATIONS
from .installer import (
    InstallError,
    download_artifact,
    install_verified_artifact,
    preview_installation,
    verify_local_artifact,
)
from .models import Application, SystemProfile
from .selection import select_artifact


def _launcher_version() -> str:
    """Return the installed distribution version, with a source-checkout fallback."""
    try:
        return distribution_version("linux-software-lab-center")
    except PackageNotFoundError:
        return "0.1.0.dev1 (source checkout)"


def _ecosystem_payload(service: CatalogService, profile: SystemProfile) -> dict[str, object]:
    """Build local diagnostics without making network calls or trusting remote commands."""
    snapshot = service.load()
    integration_ids = [application_id for application_id, _commands in LOCAL_INTEGRATIONS]
    installed_ids = [
        app.id for app in snapshot.applications if executable_for(app.id)
    ]
    status_counts = dict(sorted(Counter(app.status for app in snapshot.applications).items()))
    return {
        "launcher": {
            "name": "Linux Software Lab Center",
            "version": _launcher_version(),
            "mode": "local diagnostic; no remote health probe performed",
        },
        "source_of_truth": {
            "provider": "GitHub",
            "repository": f"https://github.com/{OWNER}/{REPOSITORY}",
            "website": WEBSITE_ROOT,
            "launcher_portal": f"{WEBSITE_ROOT}/launcher/",
            "catalog": CATALOG_URL,
            "distribution_index": DISTRIBUTION_INDEX_URL,
        },
        "local_catalog": {
            "source": snapshot.data_source,
            "updated_at": snapshot.updated_at,
            "entry_count": len(snapshot.applications),
            "status_counts": status_counts,
        },
        "system": {
            "distro_id": profile.distro_id,
            "pretty_name": profile.pretty_name,
            "family": profile.family,
            "architecture": profile.architecture,
            "package_manager": profile.package_manager,
        },
        "local_integrations": {
            "reviewed_allowlist": integration_ids,
            "registered_count": len(integration_ids),
            "detected_applications": installed_ids,
        },
        "installation": {
            "native_adapter": ".deb via APT",
            "enabled_for_detected_system": profile.family == "debian-family",
            "rpm_enabled": False,
            "arch_enabled": False,
            "flatpak_enabled": False,
            "appimage_enabled": False,
            "signed_release_metadata_available": False,
            "sha256_boundary": "SHA-256 compares bytes with trusted metadata; it is not a publisher signature.",
        },
    }


def _show_ecosystem(service: CatalogService, profile: SystemProfile, as_json: bool) -> int:
    """Show how this local launcher connects to the public Linux Software Lab ecosystem."""
    try:
        payload = _ecosystem_payload(service, profile)
    except CatalogError as exc:
        print(f"Diagnostik ekosistem gagal: katalog lokal tidak valid: {exc}", file=sys.stderr)
        return 1

    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    launcher = payload["launcher"]
    source = payload["source_of_truth"]
    catalog = payload["local_catalog"]
    system = payload["system"]
    integrations = payload["local_integrations"]
    installation = payload["installation"]
    assert isinstance(launcher, dict)
    assert isinstance(source, dict)
    assert isinstance(catalog, dict)
    assert isinstance(system, dict)
    assert isinstance(integrations, dict)
    assert isinstance(installation, dict)

    print(f"{launcher['name']} · versi {launcher['version']}")
    print(f"Sumber kebenaran : {source['provider']} · {source['repository']}")
    print(f"Website           : {source['website']}")
    print(f"Portal launcher   : {source['launcher_portal']}")
    print(f"Katalog lokal     : {catalog['entry_count']} aplikasi · {catalog['updated_at']} · {catalog['source']}")
    print(f"Status katalog    : {catalog['status_counts']}")
    print(f"Sistem            : {system['pretty_name']} · {system['family']} · {system['architecture']}")
    print(f"Integrasi lokal   : {integrations['registered_count']} target allowlist · terdeteksi: {', '.join(integrations['detected_applications']) or 'tidak ada'}")
    print(f"Adapter native    : {installation['native_adapter']} · {'tersedia untuk keluarga distro ini' if installation['enabled_for_detected_system'] else 'tidak aktif untuk distro ini'}")
    print("Adapter lain      : RPM / Arch / Flatpak / AppImage belum diaktifkan.")
    print("Kepercayaan rilis : metadata bertanda tangan belum tersedia; SHA-256 bukan tanda tangan penerbit.")
    print("Catatan           : diagnosa ini bersifat lokal; tidak melakukan probe jaringan atau mengubah sistem.")
    return 0


def _print_profile(profile: SystemProfile) -> None:
    print(f"Sistem       : {profile.pretty_name}")
    print(f"ID distro    : {profile.distro_id}")
    print(f"Keluarga     : {profile.family}")
    print(f"Arsitektur   : {profile.architecture}")
    print(f"Package mgr  : {profile.package_manager or 'belum dikenali'}")
    print(f"pkexec/Polkit : {'tersedia' if profile.pkexec_path else 'tidak ditemukan'}")


def _show_list(service: CatalogService, profile: SystemProfile, as_json: bool) -> int:
    snapshot = service.load()
    if as_json:
        payload = []
        for app in snapshot.applications:
            installed_executable = executable_for(app.id)
            available = [
                {
                    "version": artifact.version,
                    "format": artifact.format,
                    "status": artifact.release_status,
                    "sha256": artifact.sha256,
                }
                for artifact in app.artifacts
                if artifact_compatibility(artifact, profile)[0]
            ]
            payload.append(
                {
                    "id": app.id,
                    "name": app.name,
                    "version": app.version,
                    "status": app.status,
                    "installed": bool(installed_executable),
                    "website_url": f"{WEBSITE_ROOT}{app.detail_url}",
                    "source_url": app.source_url,
                    "available_artifacts": available,
                }
            )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(f"Linux Software Lab Center · katalog {snapshot.updated_at} ({snapshot.data_source})")
    _print_profile(profile)
    print()
    for app in snapshot.applications:
        installed = "terpasang" if executable_for(app.id) else "belum terdeteksi terpasang"
        compatible = [
            artifact for artifact in app.artifacts
            if artifact_compatibility(artifact, profile)[0]
        ]
        formats = ", ".join(f".{artifact.format}" for artifact in compatible) or "belum ada paket cocok"
        print(f"{app.name} ({app.id})")
        print(f"  versi katalog : {app.version} · {app.status}")
        print(f"  aplikasi      : {installed}")
        print(f"  paket         : {formats}")
        print(f"  ringkasan     : {app.summary}")
        print(f"  website       : {WEBSITE_ROOT}{app.detail_url}")
        if app.source_url:
            print(f"  repositori    : {app.source_url}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lsl",
        description="Linux Software Lab Center — katalog desktop dan CLI berbagi core kompatibilitas.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_launcher_version()}",
        help="Tampilkan versi launcher.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    ecosystem_parser = sub.add_parser(
        "ecosystem",
        help="Diagnostik lokal untuk integrasi website, katalog, dan adapter launcher.",
    )
    ecosystem_parser.add_argument(
        "--json",
        action="store_true",
        help="Keluarkan diagnostik dalam JSON untuk skrip/tooling.",
    )
    sub.add_parser("detect", help="Deteksi distro, package manager, dan arsitektur lokal.")
    list_parser = sub.add_parser("list", help="Tampilkan aplikasi katalog dan status paket.")
    list_parser.add_argument("--json", action="store_true", help="Keluarkan data mesin dalam JSON.")

    info_parser = sub.add_parser("info", help="Tampilkan ringkasan aplikasi dan format paket.")
    info_parser.add_argument("application_id")

    refresh_parser = sub.add_parser("refresh", help="Segarkan cache metadata dari sumber resmi.")
    refresh_parser.add_argument("--yes", action="store_true", help="Konfirmasi bahwa metadata akan diunduh dari GitHub.")

    download_parser = sub.add_parser("download", help="Unduh dan verifikasi paket/arsip.")
    download_parser.add_argument("application_id")
    download_parser.add_argument("--version")
    download_parser.add_argument("--format", dest="requested_format")

    verify_parser = sub.add_parser("verify", help="Verifikasi file lokal terhadap manifest rilis dan SHA-256.")
    verify_parser.add_argument("application_id")
    verify_parser.add_argument("file", type=Path)
    verify_parser.add_argument("--version")
    verify_parser.add_argument("--format", dest="requested_format", required=True)

    install_parser = sub.add_parser("install", help="Tinjau lalu pasang paket native yang kompatibel.")
    install_parser.add_argument("application_id")
    install_parser.add_argument("--version")
    install_parser.add_argument("--dry-run", action="store_true", help="Unduh, verifikasi, dan simulasi tanpa memasang.")

    sub.add_parser("status", help="Tampilkan status lokal aplikasi yang bisa ditemukan.")
    sub.add_parser("doctor", help="Periksa dependensi lokal untuk fungsi launcher.")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    service: CatalogService | None = None,
    profile: SystemProfile | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    catalog_service = service or CatalogService()
    system_profile = profile or detect_system_profile()

    if args.command == "ecosystem":
        return _show_ecosystem(catalog_service, system_profile, args.json)

    if args.command == "detect":
        _print_profile(system_profile)
        if system_profile.family == "unknown":
            print("Catatan: distro ini belum memiliki adapter native yang dikenali.")
        return 0

    if args.command == "refresh":
        if not args.yes:
            print("Refresh mengunduh dua file JSON katalog dari GitHub dan mengganti cache lokal.")
            print("Ketik REFRESH untuk melanjutkan: ", end="", flush=True)
            try:
                confirmation = input().strip()
            except EOFError:
                confirmation = ""
            if confirmation != "REFRESH":
                print("Refresh dibatalkan.")
                return 2
        try:
            refreshed = catalog_service.refresh()
        except CatalogError as exc:
            print(f"Gagal memperbarui metadata: {exc}", file=sys.stderr)
            return 1
        print(f"Katalog diperbarui: {len(refreshed.applications)} aplikasi · {refreshed.updated_at}")
        return 0

    if args.command == "list":
        try:
            return _show_list(catalog_service, system_profile, args.json)
        except CatalogError as exc:
            print(f"Katalog tidak valid: {exc}", file=sys.stderr)
            return 1

    if args.command == "status":
        try:
            snapshot = catalog_service.load()
        except CatalogError as exc:
            print(f"Katalog tidak valid: {exc}", file=sys.stderr)
            return 1
        for app in snapshot.applications:
            executable = executable_for(app.id)
            if executable:
                print(f"{app.name}: terdeteksi ({executable})")
            else:
                print(f"{app.name}: belum terdeteksi terpasang")
        return 0

    if args.command == "doctor":
        try:
            snapshot = catalog_service.load()
        except CatalogError as exc:
            print(f"Metadata: GAGAL · {exc}")
            return 1
        print(f"Metadata offline : OK · {len(snapshot.applications)} aplikasi")
        print(f"Python           : {sys.version.split()[0]}")
        print(f"Distro           : {system_profile.pretty_name} ({system_profile.family})")
        print(f"Arsitektur       : {system_profile.architecture}")
        for command in ("curl", "flatpak", "pkexec", "apt-get", "dnf", "zypper", "pacman"):
            print(f"{command:16}: {shutil.which(command) or 'tidak ditemukan'}")
        if system_profile.family != "debian-family":
            print("Instalasi paket .deb: tidak tersedia untuk distro ini.")
        return 0

    try:
        snapshot = catalog_service.load()
    except CatalogError as exc:
        print(f"Katalog tidak valid: {exc}", file=sys.stderr)
        return 1
    app: Application | None = snapshot.find(args.application_id)
    if app is None:
        print(f"Aplikasi tidak ditemukan dalam katalog: {args.application_id}", file=sys.stderr)
        return 2

    if args.command == "info":
        print(f"{app.name} ({app.id})")
        print(f"Versi katalog : {app.version}")
        print(f"Status        : {app.status}")
        print(f"Kategori      : {app.category}")
        print(f"Ringkasan     : {app.summary}")
        print(f"Detail        : {app.description}")
        print(f"Halaman web  : {WEBSITE_ROOT}{app.detail_url}")
        if app.source_url:
            print(f"Sumber GitHub: {app.source_url}")
        print("Artefak:")
        if not app.artifacts:
            print("  Belum ada paket/arsip rilis yang terdaftar.")
        for artifact in app.artifacts:
            compatible, reason = artifact_compatibility(artifact, system_profile)
            marker = "cocok" if compatible else "tidak dipasang langsung"
            print(f"  {artifact.version} .{artifact.format} · {artifact.release_status} · {marker}")
            print(f"    {reason}")
        for target in app.planned_targets:
            print(f"  TARGET DIRENCANAKAN · {target.distribution_id} · {target.version}")
            print(f"    {target.note}")
        if app.source_url:
            print(f"Sumber        : {app.source_url}")
        return 0

    if args.command == "download":
        artifact = select_artifact(
            app, system_profile, version=args.version, requested_format=args.requested_format
        )
        if artifact is None:
            print("Tidak ada artefak yang terdaftar untuk aplikasi/versi tersebut.", file=sys.stderr)
            return 2
        try:
            path = download_artifact(artifact)
        except InstallError as exc:
            print(f"Unduhan ditolak/gagal: {exc}", file=sys.stderr)
            return 1
        print(f"Unduhan terverifikasi: {path}")
        print(f"SHA-256: {artifact.sha256}")
        if artifact.is_source_archive:
            print("Ini arsip source, bukan paket instalasi native.")
        elif artifact.release_status == "testing":
            print("Catatan: rilis berstatus testing/Beta.")
        return 0

    if args.command == "verify":
        artifact = select_artifact(
            app,
            system_profile,
            version=args.version,
            requested_format=args.requested_format,
        )
        if artifact is None:
            print("Artefak tidak ditemukan di metadata rilis.", file=sys.stderr)
            return 2
        try:
            digest = verify_local_artifact(artifact, args.file)
        except InstallError as exc:
            print(f"Verifikasi gagal: {exc}", file=sys.stderr)
            return 1
        print(f"Verifikasi berhasil: {args.file.resolve()}")
        print(f"SHA-256: {digest}")
        return 0

    if args.command == "install":
        artifact = select_artifact(
            app, system_profile, version=args.version, install_only=True
        )
        if artifact is None:
            print(f"Belum ada paket native yang cocok untuk {app.name} pada sistem ini.")
            print(f"Distro: {system_profile.pretty_name} · keluarga: {system_profile.family}")
            print("Launcher tidak mengganti paket dengan format distro lain.")
            if app.source_url:
                print(f"Source tersedia untuk ditinjau: {app.source_url}")
            return 3
        if artifact.release_status == "testing":
            print(
                f"PERINGATAN: {app.name} {artifact.version} berstatus Beta/testing. "
                "SHA-256 memeriksa integritas file, bukan tanda tangan penerbit."
            )
        if not args.dry_run:
            print(f"Ketik PASANG {app.id} untuk mengunduh dan meninjau paket: ", end="", flush=True)
            try:
                answer = input().strip()
            except EOFError:
                answer = ""
            if answer != f"PASANG {app.id}":
                print("Instalasi dibatalkan.")
                return 2
        try:
            package_path = download_artifact(artifact)
            print(f"Paket diunduh dan diverifikasi: {package_path}")
            preview = preview_installation(artifact, package_path, system_profile)
        except InstallError as exc:
            print(f"Instalasi dihentikan: {exc}", file=sys.stderr)
            return 1
        print("\nRencana APT (simulasi; belum mengubah sistem):")
        print(preview.output)
        if args.dry_run:
            print("\nDry-run selesai; tidak ada perubahan pada sistem.")
            return 0
        print("\nKetik LANJUTKAN untuk meminta otorisasi Polkit dan memasang paket: ", end="", flush=True)
        try:
            answer = input().strip()
        except EOFError:
            answer = ""
        if answer != "LANJUTKAN":
            print("Instalasi dibatalkan; tidak ada transaksi yang dijalankan.")
            return 2
        try:
            result = install_verified_artifact(
                artifact,
                package_path,
                system_profile,
                expected_preview=preview,
            )
        except InstallError as exc:
            print(f"Instalasi gagal dengan aman: {exc}", file=sys.stderr)
            return 1
        if result.success:
            print("Package manager menyatakan instalasi selesai.")
            if result.output:
                print(result.output)
            return 0
        print(f"Package manager keluar dengan kode {result.return_code}.", file=sys.stderr)
        if result.output:
            print(result.output, file=sys.stderr)
        return result.return_code or 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
