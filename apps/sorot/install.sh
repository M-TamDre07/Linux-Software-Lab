#!/usr/bin/env bash
# Sorot distribution-aware installer.
# Downloads only a package declared in a versioned release manifest and verifies SHA-256 before installation.
set -Eeuo pipefail

readonly RAW_ROOT="https://raw.githubusercontent.com/M-TamDre07/Linux-Software-Lab/main/apps/sorot"
readonly INDEX_URL="${RAW_ROOT}/releases/index.json"

VERSION=""
ACTION="install"
ASSUME_YES=0
DRY_RUN=0

usage() {
  cat <<'USAGE'
Sorot installer — Linux

Usage:
  bash install.sh [--version X.Y.Z] [--yes] [--dry-run]
  bash install.sh --list
  bash install.sh --detect
  bash install.sh --help

Options:
  --version X.Y.Z  Select an explicitly indexed Sorot version. Without it,
                   choose the newest indexed version that has a package for
                   the detected distribution.
  --list           List published version artifacts and planned targets.
  --detect         Show the distribution family and package format expected.
  --dry-run        Download and verify a compatible package, but do not install it.
  --yes            Skip the prompt for a beta/testing package.
  --help           Show this message.

The script never substitutes a .deb package on Arch Linux. A distribution is
considered installable only when the version manifest contains a compatible,
checksummed package artifact.
USAGE
}

die() { printf 'Sorot installer: %s\n' "$*" >&2; exit 1; }
note() { printf 'Sorot installer: %s\n' "$*"; }

while (($#)); do
  case "$1" in
    --version)
      (($# >= 2)) || die "--version needs a version value."
      VERSION="$2"
      shift 2
      ;;
    --list)
      ACTION="list"
      shift
      ;;
    --detect)
      ACTION="detect"
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --yes)
      ASSUME_YES=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      die "Unknown option: $1 (see --help)."
      ;;
  esac
done

if [[ -n "$VERSION" ]]; then
  [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+([+-][A-Za-z0-9.-]+)?$ ]] || die "Invalid version string: $VERSION"
fi

if [[ ! -r /etc/os-release ]]; then
  die "Cannot read /etc/os-release; automatic distribution-family detection is unavailable."
fi
# shellcheck disable=SC1091
. /etc/os-release
DISTRO_ID="$(printf '%s' "${ID:-unknown}" | tr '[:upper:]' '[:lower:]')"
DISTRO_LIKE="$(printf '%s' "${ID_LIKE:-}" | tr '[:upper:]' '[:lower:]')"
DISTRO_NAME="${PRETTY_NAME:-$DISTRO_ID}"
DISTRO_FAMILY="unknown"
PACKAGE_FORMAT=""
PACKAGE_MANAGER=""

case "$DISTRO_ID $DISTRO_LIKE" in
  *debian*|*ubuntu*|*linuxmint*|*pop*|*zorin*|*elementary*|*kali*|*raspbian*|*deepin*)
    DISTRO_FAMILY="debian-family"
    PACKAGE_FORMAT="deb"
    PACKAGE_MANAGER="apt"
    ;;
  *arch*|*manjaro*|*endeavouros*|*artix*|*cachyos*|*garuda*)
    DISTRO_FAMILY="arch-family"
    PACKAGE_FORMAT="pkg.tar.zst"
    PACKAGE_MANAGER="pacman"
    ;;
  *fedora*|*rhel*|*centos*|*rocky*|*almalinux*|*nobara*)
    DISTRO_FAMILY="fedora-family"
    PACKAGE_FORMAT="rpm"
    PACKAGE_MANAGER="dnf"
    ;;
  *opensuse*|*suse*|*sled*|*sles*)
    DISTRO_FAMILY="suse-family"
    PACKAGE_FORMAT="rpm"
    PACKAGE_MANAGER="zypper"
    ;;
esac

if [[ "$ACTION" == "detect" ]]; then
  note "Detected OS: $DISTRO_NAME (ID=$DISTRO_ID; ID_LIKE=${DISTRO_LIKE:-not reported})."
  if [[ -n "$PACKAGE_FORMAT" ]]; then
    note "Distribution family: $DISTRO_FAMILY; expected native package format: .$PACKAGE_FORMAT; package manager: $PACKAGE_MANAGER."
    note "Detection is only a distro-family hint. The version manifest must still contain a compatible package before installation can proceed."
    note "Run --list to inspect real indexed artifacts; detection does not mean that a compatible package has been published."
  else
    note "No package-manager mapping is implemented for this distribution. No native installer will be selected."
  fi
  exit 0
fi

command -v curl >/dev/null 2>&1 || die "curl is required to fetch the version manifest and package."
command -v python3 >/dev/null 2>&1 || die "python3 is required to validate JSON release metadata."
command -v sha256sum >/dev/null 2>&1 || die "sha256sum is required to verify package integrity."

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

curl --fail --location --silent --show-error --max-time 30 --retry 2 "$INDEX_URL" -o "$TMP_DIR/index.json" \
  || die "Could not download the Sorot release index."
python3 - "$TMP_DIR/index.json" <<'PY' >/dev/null || die "The Sorot release index is invalid."
import json, sys
with open(sys.argv[1], encoding="utf-8") as stream:
    data = json.load(stream)
if data.get("schema_version") != 1 or data.get("product") != "Sorot":
    raise SystemExit("unexpected release index schema/product")
if not isinstance(data.get("versions"), list):
    raise SystemExit("versions must be a list")
for entry in data["versions"]:
    if not isinstance(entry, dict) or not isinstance(entry.get("version"), str):
        raise SystemExit("invalid version index entry")
PY

if [[ "$ACTION" == "list" ]]; then
  python3 - "$TMP_DIR/index.json" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as stream:
    data = json.load(stream)
print("Sorot: published version archive")
for item in data["versions"]:
    formats = ", ".join("." + f for f in item.get("formats", [])) or "formats not listed"
    print(f"  {item['version']} — {item.get('channel', 'unknown')} / {item.get('status', 'unknown')}: {formats}")
planned = data.get("planned_targets", [])
if planned:
    print("\nPlanned targets (not downloadable):")
    for item in planned:
        print(f"  {item.get('version', '?')} — {item.get('distribution', 'distribution')}: {item.get('status', 'planned')}; expected format .{item.get('expected_format', 'unknown')}")
        print(f"    {item.get('note', '')}")
PY
  exit 0
fi

if [[ -z "$PACKAGE_FORMAT" ]]; then
  die "No native package format is configured for $DISTRO_NAME. Check --list for real artifacts; do not install another distribution's package."
fi

command -v "$PACKAGE_MANAGER" >/dev/null 2>&1 || die "$PACKAGE_MANAGER is not installed on this system."

mapfile -t INDEXED_VERSIONS < <(python3 - "$TMP_DIR/index.json" <<'PY'
import json, re, sys
with open(sys.argv[1], encoding="utf-8") as stream:
    data = json.load(stream)
versions = []
for item in data["versions"]:
    version = item.get("version", "")
    if re.fullmatch(r"\d+\.\d+\.\d+(?:[+-][A-Za-z0-9.-]+)?", version):
        versions.append(version)
for version in reversed(versions):
    print(version)
PY
)
[[ "${#INDEXED_VERSIONS[@]}" -gt 0 ]] || die "The version index contains no selectable releases."

if [[ -n "$VERSION" ]]; then
  FOUND_VERSION=0
  for item in "${INDEXED_VERSIONS[@]}"; do
    [[ "$item" == "$VERSION" ]] && FOUND_VERSION=1
  done
  ((FOUND_VERSION == 1)) || die "Version $VERSION is not in the published version index."
  CANDIDATES=("$VERSION")
else
  CANDIDATES=("${INDEXED_VERSIONS[@]}")
fi

SELECTED_VERSION=""
SELECTED_FILE=""
SELECTED_SHA=""
SELECTED_STATUS=""
SELECTED_CHANNEL=""

for candidate in "${CANDIDATES[@]}"; do
  manifest="$TMP_DIR/manifest-$candidate.json"
  curl --fail --location --silent --show-error --max-time 30 --retry 2 \
    "${RAW_ROOT}/releases/$candidate/release.json" -o "$manifest" \
    || die "Could not fetch manifest for indexed version $candidate."
  artifact_info="$(python3 - "$manifest" "$candidate" "$PACKAGE_FORMAT" <<'PY'
import json, os, re, sys
manifest_path, wanted_version, wanted_format = sys.argv[1:]
try:
    with open(manifest_path, encoding="utf-8") as stream:
        data = json.load(stream)
except (OSError, json.JSONDecodeError) as exc:
    raise SystemExit(f"invalid release manifest: {exc}")
if data.get("schema_version") != 1 or data.get("product") != "Sorot":
    raise SystemExit("unexpected manifest schema/product")
if data.get("version") != wanted_version:
    raise SystemExit("manifest version does not match the requested directory")
status = data.get("status")
if status not in {"testing", "released", "archived"}:
    raise SystemExit("unsupported release status")
if status == "archived":
    print("")
    raise SystemExit(0)
if not isinstance(data.get("artifacts"), list):
    raise SystemExit("manifest artifacts must be a list")
allowed_kinds = {
    "deb": {"debian-package", "distro-package"},
    "pkg.tar.zst": {"arch-package", "distro-package"},
    "rpm": {"rpm-package", "distro-package"},
}
suffixes = {"deb": ".deb", "pkg.tar.zst": ".pkg.tar.zst", "rpm": ".rpm"}
import platform
machine = platform.machine().lower()
architecture_aliases = {
    "x86_64": {"x86_64", "amd64"},
    "amd64": {"amd64", "x86_64"},
    "aarch64": {"aarch64", "arm64"},
    "arm64": {"arm64", "aarch64"},
    "armv7l": {"armv7l", "armhf"},
}
compatible_architectures = architecture_aliases.get(machine, {machine})
for item in data["artifacts"]:
    if not isinstance(item, dict) or item.get("format") != wanted_format:
        continue
    filename = item.get("file")
    digest = item.get("sha256")
    kind = item.get("kind")
    architecture = item.get("architecture", "all")
    if not isinstance(filename, str) or not filename or os.path.basename(filename) != filename:
        raise SystemExit("artifact filename must be a plain filename")
    if not filename.endswith(suffixes[wanted_format]):
        raise SystemExit("artifact filename suffix does not match its format")
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise SystemExit("artifact SHA-256 is invalid")
    if kind not in allowed_kinds[wanted_format]:
        raise SystemExit("artifact kind does not match the native package format")
    if architecture not in {"all", "any", "noarch"} and architecture not in compatible_architectures:
        continue
    print("\t".join([filename, digest, status, str(data.get("channel", "unknown")), kind, architecture]))
    raise SystemExit(0)
print("")
PY
)" || die "The manifest for version $candidate failed validation."
  if [[ -n "$artifact_info" ]]; then
    IFS=$'\t' read -r SELECTED_FILE SELECTED_SHA SELECTED_STATUS SELECTED_CHANNEL _KIND _ARCH <<< "$artifact_info"
    SELECTED_VERSION="$candidate"
    break
  fi
done

if [[ -z "$SELECTED_VERSION" ]]; then
  if [[ "$DISTRO_FAMILY" == "arch-family" ]]; then
    planned_target="$(python3 - "$TMP_DIR/index.json" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as stream:
    data = json.load(stream)
for item in data.get("planned_targets", []):
    if str(item.get("distribution", "")).casefold() == "arch linux" and item.get("status") == "planned":
        print(f"{item.get('version', 'future version')} (planned, not downloadable)")
        break
PY
)"
    if [[ -n "$planned_target" ]]; then
      die "No .pkg.tar.zst artifact is published for this distribution. Roadmap: Arch Linux $planned_target. Source archives are for manual review/build only."
    fi
    die "No .pkg.tar.zst artifact is published for this distribution in the indexed versions. Do not install a .deb as a fallback."
  fi
  die "No compatible .$PACKAGE_FORMAT package is published for $DISTRO_NAME in the indexed versions. Check --list for available formats."
fi

note "Detected: $DISTRO_NAME ($DISTRO_FAMILY)."
note "Selected Sorot $SELECTED_VERSION ($SELECTED_CHANNEL / $SELECTED_STATUS): $SELECTED_FILE."
note "The SHA-256 will be checked against the version manifest before the package manager is invoked."

if [[ "$SELECTED_STATUS" == "testing" && "$ASSUME_YES" -ne 1 && "$DRY_RUN" -ne 1 ]]; then
  [[ -t 0 ]] || die "This is a beta/testing build. Run interactively to confirm, or pass --yes to explicitly accept the beta."
  printf 'Sorot %s is a beta/testing build, not a stable release. Continue? [y/N] ' "$SELECTED_VERSION"
  read -r answer
  [[ "$answer" == "y" || "$answer" == "Y" ]] || die "Installation cancelled."
fi

PACKAGE_PATH="$TMP_DIR/$SELECTED_FILE"
PACKAGE_URL="${RAW_ROOT}/releases/$SELECTED_VERSION/$SELECTED_FILE"
curl --fail --location --silent --show-error --max-time 120 --retry 2 "$PACKAGE_URL" -o "$PACKAGE_PATH" \
  || die "Package download failed: $SELECTED_FILE"

ACTUAL_SHA="$(sha256sum "$PACKAGE_PATH" | awk '{print $1}')"
[[ "$ACTUAL_SHA" == "$SELECTED_SHA" ]] || die "SHA-256 mismatch for $SELECTED_FILE. The package will not be installed."

note "SHA-256 verification passed."
if ((DRY_RUN)); then
  note "Dry-run complete. Verified package file: $SELECTED_FILE; no package manager was run."
  exit 0
fi

run_package_manager() {
  if ((EUID == 0)); then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    die "Root privileges are needed to install the verified package; install sudo or run the script as root."
  fi
}

case "$PACKAGE_MANAGER" in
  apt) run_package_manager apt install "$PACKAGE_PATH" ;;
  pacman) run_package_manager pacman -U "$PACKAGE_PATH" ;;
  dnf) run_package_manager dnf install "$PACKAGE_PATH" ;;
  zypper) run_package_manager zypper install "$PACKAGE_PATH" ;;
esac

note "Package manager finished. Keep the version manifest and checksum details if you need to audit this installation."
