# Publikasi PaketScope 3.0.0.dev5 ke repo

Folder ini memakai struktur repo yang sama persis. Salin isinya ke root repo `M-TamDre07/Linux-Software-Lab`.

## Lokasi dan alasannya

- `apps/paketscope/releases/3.0.0.dev5/`: folder rilis. Polanya sama dengan `apps/sorot/releases/0.7.0/`.
- `apps/paketscope/packaging/repo/`: alat repositori APT (`build-apt-repo.sh`) dan panduan pengguna. Ini tooling, bukan artefak rilis.
- Bukan di `public/`: `public/` adalah data dan situs yang tampil ke pengunjung. Itu butuh persetujuan terpisah.

## Langkah

1. Buat branch dari `main`:

       git checkout -b release/paketscope-3.0.0.dev5 origin/main

2. Terapkan perubahan sumber (patch ini sudah diuji bisa diterapkan ke `main` bersih):

       git apply apps/paketscope/releases/3.0.0.dev5/paketscope-3.0.0.dev5-vs-main.patch

3. Salin folder rilis dan tooling ke repo (`apps/paketscope/releases/` dan `apps/paketscope/packaging/repo/`).

4. Verifikasi checksum dari folder rilis:

       cd apps/paketscope/releases/3.0.0.dev5 && sha256sum -c SHA256SUMS

5. Jalankan CI. Workflow `paketscope-build.yml` harus lulus, termasuk gerbang lintian.

6. Buka PR ke `main`, tinjau, lalu merge.

## Yang TIDAK ikut dipublikasikan

- Kunci uji di `repo/TEST-ONLY-demo-repo/`. Kunci itu hanya untuk uji lokal dan tidak boleh masuk repo.
- Folder `repo/` dari paket sementara sebelumnya. Hanya `packaging/repo/` yang relevan.

## Yang perlu persetujuan terpisah

- Menambahkan `releaseUrl` PaketScope di `public/data/software.json`. Ini mengubah apa yang dilihat pengunjung website.
- Membuat `apps/paketscope/releases/index.json`. Validator Sorot belum mencakup PaketScope.
- Menghosting repositori APT dan memasang kunci rilis milik Anda sendiri.

## Batasan yang harus dibaca sebelum merge

- Status rilis: `testing`, bukan stable. Syaratnya ada di `TEST-REPORT.md`.
- Dukungan: Debian 13 terbatas. Belum diinstal di Debian 13 sungguhan.
- `fedora/` dan `arch/` bersifat eksperimental dan belum dibangun di distro itu.
