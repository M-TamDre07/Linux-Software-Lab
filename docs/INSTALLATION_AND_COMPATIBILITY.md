# Instalasi dan kompatibilitas LISO LAB

Dokumen ini menjelaskan alur pengguna akhir dan hubungan layanan publik. GitHub adalah sumber data dan kode yang otoritatif; Vercel menerbitkan website statis; Supabase menyimpan mirror katalog baca-saja.

## Status artefak saat ini

Status berikut diverifikasi dari manifest rilis Sorot 1.0.23 dan katalog proyek pada 24 November 2026. "Terdeteksi" tidak sama dengan "didukung": installer bisa mengenali sebuah keluarga distro tanpa memiliki paket yang cocok.

| Platform | Artefak aktual | Status |
| --- | --- | --- |
| Debian / Ubuntu dan turunan kompatibel | Sorot `.deb` | Tersedia. Debian 13 adalah target smoke test CI saat ini; turunan lain perlu verifikasi masing-masing. |
| Arch Linux | `.pkg.tar.zst` | Belum diterbitkan; hanya target rencana. |
| Fedora / RHEL | `.rpm` | Belum diterbitkan. |
| openSUSE / SUSE | `.rpm` | Belum diterbitkan. |
| Linux lain | — | Tidak ada paket native yang dinyatakan kompatibel. |
| Lingkungan Python | Python wheel | Tersedia untuk lingkungan Python dan dependensi yang cocok; bukan paket native OS. |

PaketScope 3.0.0.dev5 adalah pratinjau pengembangan dan tidak boleh dipromosikan sebagai installer stabil. Linux Software Lab Center juga masih dalam pengembangan. Jangan menampilkan perintah pemasangan untuk format yang tidak ada pada manifest.

## Instal Sorot dari terminal

Jalankan perintah berikut dari akun pengguna biasa. Installer akan menggunakan `sudo` hanya ketika package manager membutuhkan hak administrator. **Jangan jalankan skrip installer dengan `sudo bash`.**

Unduh skrip resmi dan lihat isinya:

```bash
curl --fail --location --show-error --max-time 30 \
  https://raw.githubusercontent.com/M-TamDre07/Linux-Software-Lab/main/apps/sorot/install.sh \
  --output /tmp/sorot-install.sh

sed -n '1,260p' /tmp/sorot-install.sh
```

Deteksi distro dan lihat daftar artefak:

```bash
bash /tmp/sorot-install.sh --detect
bash /tmp/sorot-install.sh --list
```

Jalankan dry-run. Langkah ini mengunduh artefak yang cocok dan memeriksa SHA-256, tetapi tidak menjalankan package manager:

```bash
bash /tmp/sorot-install.sh --version 1.0.23 --dry-run
```

Setelah distro dan checksum terverifikasi, lakukan pemasangan:

```bash
bash /tmp/sorot-install.sh --version 1.0.23
```

Jika distro adalah Arch, Fedora, openSUSE, atau sistem lain yang belum mempunyai artefak native, installer harus berhenti dengan pesan tidak tersedia. Itu perilaku yang disengaja agar paket dari keluarga distro lain tidak dipasang sebagai fallback.

Untuk mengetahui opsi:

```bash
bash /tmp/sorot-install.sh --help
```

## Menjalankan website dan memeriksa proyek secara lokal

Prasyarat: Python 3.10+ untuk skrip pemeriksaan, dan Node.js untuk tes JavaScript. Jalankan dari root clone repositori:

```bash
python3 -m http.server 8000 --directory public
```

Buka `http://localhost:8000/`, `http://localhost:8000/software/`, dan `http://localhost:8000/software/sorot.html`.

Pemeriksaan katalog, link, manifest, integrasi, JavaScript dan tes:

```bash
python scripts/validate_catalog.py
python scripts/check_site_links.py
python scripts/check_docs_links.py
python scripts/validate_app_manifest.py
python scripts/sync_distribution_index.py --check
python apps/sorot/validate_releases.py
node --check public/assets/js/site.js
node --check public/assets/js/sorot-downloads.js
node --test tests/test_catalog_contract.cjs
python -m unittest discover -s tests -v
```

Audit layanan produksi bersifat baca-saja:

```bash
python scripts/check_live_integrations.py
```

Skrip tersebut membandingkan katalog JSON yang diterbitkan Vercel dan mirror publik Supabase dengan sumber GitHub. Ia tidak melakukan SQL write, migrasi, atau perubahan deployment.

## Alur integritas GitHub → CI → Supabase dan Vercel

1. **GitHub** menyimpan kode, `public/data/software.json`, skema metadata, manifest rilis dan dokumen. Perubahan diajukan melalui branch dan pull request.
2. **GitHub Actions** memvalidasi format katalog, halaman, tautan, manifest rilis, checksum, dan tes aplikasi. Pull request hanya menjalankan validasi; sinkronisasi database produksi tidak dijalankan dari kode PR.
3. Setelah perubahan yang ditinjau masuk ke `main`, workflow tepercaya menyinkronkan `software_catalog` di Supabase. Kunci rahasia hanya disimpan di GitHub Actions Secrets. Website browser hanya memakai publishable key dan akses SELECT yang dibatasi RLS.
4. **Vercel** membangun deployment dari repositori yang sama. Root Directory tetap root repositori; Output Directory `public/`. Kode aplikasi, tes, dan dokumen di luar `public/` tidak diterbitkan sebagai website.
5. Website membaca katalog Supabase bila tersedia dan fallback ke `/data/software.json` dari deployment yang sama bila mirror gagal.
6. Pemeriksaan live integritas membandingkan katalog GitHub, Vercel dan Supabase. Perbedaan dilaporkan untuk ditinjau; jangan memperbaiki drift dengan menulis langsung dari browser.

## Batas keamanan dan kompatibilitas

- Jangan pernah memasukkan Supabase `sb_secret_` atau service-role key ke JavaScript publik, HTML, atau variabel `NEXT_PUBLIC_`.
- Jangan membuat policy publik untuk tabel OTP, sesi verifikasi, atau tautan Telegram. RLS yang aktif tanpa policy mencegah akses langsung dari klien biasa.
- Jangan menjalankan aplikasi GUI seluruhnya sebagai root. Hak administrator hanya untuk operasi package manager yang sempit dan sudah dikonfirmasi.
- Jangan menganggap browser dapat membaca `/etc/os-release`. Website meminta pengunjung memilih distro secara manual; installer native membaca distro langsung dari sistem.
- Jangan mengartikan SHA-256 sebagai tanda tangan penerbit. Verifikasi checksum melindungi terhadap mismatch file dengan metadata yang diperoleh, bukan identitas kriptografis pembuat.
- Jangan menyimpulkan dukungan distro, desktop, Wayland/X11, atau arsitektur hanya dari user-agent atau dari paket `all`. Klaim kompatibilitas harus ditautkan ke artefak, manifest dan pengujian yang nyata.

Rincian deployment ada di [VERCEL_DEPLOYMENT.md](VERCEL_DEPLOYMENT.md), model database di [SUPABASE_INTEGRATION.md](SUPABASE_INTEGRATION.md), dan aturan UI di [WEBSITE_MAINTENANCE.md](WEBSITE_MAINTENANCE.md).