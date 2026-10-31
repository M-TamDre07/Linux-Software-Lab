# Rust Adoption Strategy

**Status:** Proposed foundation / no Rust runtime component approved yet  
**Date:** 2026-10-31  
**Scope:** Linux Software Lab website, Sorot, PaketScope, and Linux Software Lab Center

## Decision

Rust is an approved technology option for carefully selected systems components in Linux Software Lab. It is **not** a mandate to rewrite existing applications. The current Python/PySide6 desktop applications and static HTML/CSS/JavaScript website remain the supported implementation until a specific requirement demonstrates that Rust provides a measurable benefit.

This document establishes the architecture and release gates for introducing Rust later. It does not add a Rust runtime dependency, change application behavior, or claim that Rust support is already implemented.

## Why consider Rust?

Rust is useful where explicit memory-safety guarantees, predictable performance, concurrency, and low-level operating-system integration are valuable. Safe Rust can prevent broad classes of memory errors, but it does not automatically prevent logic flaws, unsafe API design, permission mistakes, supply-chain risks, or vulnerabilities in dependencies.

There is real ecosystem activity: the Linux kernel documents Rust support behind `CONFIG_RUST`, and Microsoft publishes official guidance for Rust development on Windows. That is evidence of cross-platform relevance, not a reason to rewrite every codebase. This project does not assume that Apple has adopted Rust as a general replacement for its existing systems languages; claims about Apple's internal language strategy need a specific primary source before being repeated.

References:
- [Linux kernel: Programming Language](https://docs.kernel.org/process/programming-language.html)
- [Linux kernel: Rust documentation](https://docs.kernel.org/rust/)
- [Microsoft Learn: Develop on Windows with Rust](https://learn.microsoft.com/en-us/windows/dev-environment/rust/)

## Existing technology boundaries

| Area | Current implementation | Direction |
| --- | --- | --- |
| Public website | Static HTML, CSS, JavaScript, JSON | Keep dependency-light; Rust is not needed in browser pages. |
| Sorot | Python and PySide6 | Preserve current UI and application behavior; consider Rust only for a proven isolated systems need. |
| PaketScope | Python and PySide6, Debian/APT-focused | Keep the existing service boundaries; do not rewrite package operations merely to change language. |
| Linux Software Lab Center | Python CLI and PySide6 GUI with a shared Python core | First candidate for a narrowly scoped Rust pilot, only after the Debian baseline and current behavior are covered by tests. |
| Release/catalogue metadata | Versioned JSON manifests and GitHub as canonical source | Keep one schema and one canonical source; language changes must not create competing catalogues. |

## Preferred first candidate

The first candidate for a Rust pilot is a small **platform-core component** for Linux Software Lab Center. Its proposed responsibility is limited to deterministic, testable operations that are currently part of the launcher's shared platform/catalogue core:

- Parse Linux distribution identity from `/etc/os-release` as data; never execute or `source` that file as shell code.
- Normalize known CPU architecture aliases such as `x86_64` / `amd64` and `aarch64` / `arm64`, while preserving unknown values and failing closed when no artifact matches.
- Evaluate a versioned compatibility input against the existing distribution and artifact metadata contracts.
- Return structured decisions and diagnostics; do not perform package installation, privilege escalation, network downloads, or arbitrary command execution.

This is a **candidate**, not an approved replacement. Before implementation, freeze representative Python behavior with fixtures and contract tests. A Rust prototype must demonstrate exact parity, clearer failure behavior, or a measurable operational benefit before it can replace any Python path.

## Integration boundary

Start with a small Rust executable/library that has a versioned, machine-readable contract. Prefer JSON input/output with an explicit `schema_version` for the first pilot because it creates a visible boundary between the Rust core and the Python GUI/CLI.

The integration must:
- Invoke a fixed, packaged executable using an argument array; never build a shell command from catalogue or user-controlled text.
- Apply timeouts, bounded input/output sizes, strict JSON/schema validation, and clear exit codes.
- Keep diagnostics on stderr and machine-readable results on stdout.
- Treat missing binaries, incompatible protocol versions, malformed responses, and process failures as safe errors; do not silently fall back to a more permissive installation path.
- Keep all privileged package operations behind the reviewed Debian/APT adapter and Polkit authorization boundary. A Rust process must not run the whole GUI as root.
- Never let remote metadata select an executable path, shell command, privilege command, or arbitrary plugin.

Do not introduce Python FFI/PyO3 or unsafe cross-language bindings in the first pilot. Revisit an in-process binding only if profiling shows that process startup or serialization is a real bottleneck and a separate architecture review approves the ABI, lifecycle, packaging, and failure model.

## Distribution and architecture sequence

Keep the delivery scope deliberately narrow:

1. **Baseline:** Debian 13 (Trixie), `amd64` / `x86_64`. Validate package build, clean installation, launch, upgrade, and removal in a disposable Debian 13 environment.
2. **Second target:** Debian 13, `arm64` / `aarch64`. Build for the target and test on native ARM64 hardware or a documented emulation environment. Cross-compilation alone is not proof of runtime compatibility.
3. **Later:** Ubuntu/Debian derivatives and other Linux families only after their package dependencies, native package adapter, and lifecycle tests are defined independently.

Architecture is not the same as distribution. A Python-only package may legitimately be architecture-independent, while a package embedding a compiled Rust binary normally needs architecture-specific artifacts and correct Debian package metadata. Never label a compiled binary package `Architecture: all`.

Do not enable RPM, pacman, Flatpak, or AppImage paths as part of the Rust pilot. Distro expansion is a separate, evidence-gated project.

## Rust engineering requirements

Any approved Rust component must meet these requirements:

1. Use the official stable toolchain. Record the Rust edition and minimum supported Rust version (MSRV), and pin the toolchain used by CI.
2. Commit `Cargo.lock` for applications/binaries. Review dependency count, maintenance, licensing, security advisories, and update policy before adding crates.
3. Run `cargo fmt --all -- --check`, `cargo clippy --workspace --all-targets -- -D warnings`, and `cargo test --workspace` in CI.
4. Keep `unsafe` out of the initial implementation. Any later unsafe block requires a local safety comment, a documented reason, targeted tests, and maintainer review.
5. Add tests for malformed and adversarial inputs, unknown distributions/architectures, empty and oversized data, path traversal, timeouts, and protocol mismatch where relevant.
6. Define deterministic output, stable error codes, and backwards-compatible protocol versioning. Do not rely on log-message text as an API.
7. Build in clean, reproducible CI environments and record target triple, toolchain, dependencies, and artifact checksums.
8. Keep the runtime footprint and maintenance burden proportionate to the benefit. No framework or dependency should be added only because it is fashionable.

## Adoption gates

A Rust component may move from prototype to production only when all of the following are true:

- The Python implementation and behavior are documented by contract tests and fixtures.
- The Rust implementation passes the same contract suite and relevant security tests.
- Benchmarks or a concrete safety/maintenance argument demonstrate why the new component is worth maintaining.
- Debian 13 amd64 packaging and lifecycle tests pass without weakening existing safeguards.
- The component is tested on Debian 13 arm64 before ARM64 support is advertised.
- The Python caller handles process failure, protocol mismatch, cancellation, and timeout safely.
- Documentation, SBOM/dependency inventory where available, release manifest, checksums, and package metadata are updated.
- A rollback path to the last known-good implementation exists until the pilot is accepted.

If these gates are not met, the Rust component remains experimental and is not included in the public installer.

## Phased roadmap

| Phase | Work | Exit condition |
| --- | --- | --- |
| 0 — Stabilize | Finish the current Debian 13 amd64 release foundations for Sorot, PaketScope, and the launcher. | Existing Python paths have passing tests and repeatable Debian package lifecycle evidence. |
| 1 — Prototype | Add an isolated platform-core Rust prototype with fixtures and a versioned JSON contract. | Rust toolchain and tests run in CI; no production path depends on it. |
| 2 — Parity review | Compare Rust results with the Python reference on the same input corpus and adversarial cases. | Exact contract parity and documented measurable benefit. |
| 3 — Controlled integration | Let the launcher call the Rust component behind a reversible, tested integration boundary. | Debian 13 amd64 install/upgrade/removal and failure recovery pass. |
| 4 — ARM64 validation | Build and run the same component/package on Debian 13 arm64. | Native or clearly documented target runtime evidence; metadata accurately lists architecture. |
| 5 — Reassess | Decide whether to expand the Rust core to another application or keep it launcher-specific. | A separate ADR demonstrates a real need; no automatic mass migration. |

## Non-goals

- Rewriting Sorot, PaketScope, or the website in Rust for trend alignment.
- Replacing Python/PySide6 GUI code without a documented user-facing reason.
- Claiming all Linux distributions or CPU architectures are supported because Rust can compile to them.
- Treating memory safety as a substitute for authorization, input validation, secure packaging, or tests.
- Introducing a second source of truth for catalogue data, compatibility rules, or release metadata.
- Enabling more package managers before their native adapters and lifecycle tests pass.

## Maintainer rule

Every new Rust module must have a named owner, a bounded responsibility, a documented interface, tests, and a reason to exist. Keep the project **Debian-first, amd64-first, then arm64** until each support claim is backed by build and runtime evidence.
