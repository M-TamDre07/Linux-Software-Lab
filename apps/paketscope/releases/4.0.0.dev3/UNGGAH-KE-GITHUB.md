# Cara mengunggah PaketScope 4.0.0.dev3 ke GitHub

Anda yang mengunggah. Asisten tidak punya izin tulis ke repo.

## Cara 1: lewat patch (disarankan, bisa ditinjau)
    git clone https://github.com/M-TamDre07/Linux-Software-Lab.git
    cd Linux-Software-Lab
    git checkout -b feature/paketscope-4.0.0-dev3 origin/main
    git am /path/ke/patches/*.patch        # 6 patch, berurutan
    git push -u origin feature/paketscope-4.0.0-dev3

Lalu buka Pull Request dari cabang itu ke `main`. Jangan langsung ke `main`.

## Cara 2: lewat bundle (riwayat lengkap)
    git clone paketscope-v4-dev3.bundle paketscope-v4
    cd paketscope-v4
    git remote set-url origin https://github.com/M-TamDre07/Linux-Software-Lab.git
    git push -u origin HEAD:feature/paketscope-4.0.0-dev3

## Cara 3: salin folder sumber
Ekstrak `apps-paketscope-4.0.0.dev3-sumber.tar.gz` ke `apps/paketscope/` di repo, commit, lalu push.

## Sebelum PR digabung
- CI `paketscope-build.yml` harus lulus, termasuk gerbang lintian.
- Verifikasi checksum: `sha256sum -c SHA256SUMS`.
- Versi yang benar adalah 4.0.0.dev3 (Debian 4.0.0~dev3-1). Jangan pakai label 3.0.0.
- Keputusan yang masih terbuka ada di `HASIL-DEV3.md`.
