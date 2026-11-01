# Laporan tes — Sorot 0.7.1 Beta

Tanggal: 2026-10-29 s.d. 11-01 · Lingkungan: Ubuntu 24.04.5 x86_64 (container), akses jaringan lewat proxy. **Bukan Debian 13, bukan Arch Linux, bukan desktop nyata dengan compositor.**

> **Berbeda dari laporan 0.7.0:** kali ini PySide6, pytest, pytest-qt, ruff, mypy, lintian, desktop-file-validate, shellcheck, Xvfb dan window manager (openbox) **tersedia**, sehingga kode Qt 0.7.0 yang sebelumnya tidak pernah dijalankan akhirnya dijalankan pada Qt asli. Hasilnya: **mode cermin di 0.7.0 tidak berfungsi sama sekali**, dan ditemukan beberapa cacat lain (lihat CHANGELOG 0.7.1). Semua temuan itu sudah diperbaiki dan dijaga tes regresi.

## Hasil

| Pemeriksaan | Hasil |
|---|---|
| Suite lengkap, Python 3.13.18 + PySide6 6.12.0, Qt `offscreen` | **573 lulus**, 1 dilewati (tes penjaga platform; hanya aktif bila `SOROT_TEST_QPA` diatur) |
| Suite lengkap, Python 3.11.18 + PySide6 6.8.3 (batas bawah yang dinyatakan) | **573 lulus**, 1 dilewati |
| 128 tes GUI di **X11 nyata** (Xvfb + openbox, backend `xcb`, `make test-x11`) | **128 lulus**; tes penjaga membuktikan platform memang `xcb` |
| 128 tes GUI di **Wayland asli** (weston headless, backend `wayland`, `make test-wayland`) | **124 lulus**, 4 dilewati (fokus keyboard/clipboard: compositor tanpa seat) |
| Tes non-GUI saja | 446 lulus |
| `ruff check src tests`, `mypy src` (46 berkas) | bersih (sebelumnya 1 dan 7 temuan) |
| `scripts/release.py check` | konsisten (0.7.1) |
| `lintian` (level bawaan), `desktop-file-validate`, `shellcheck`, `dash -n` pada skrip maintainer, `groff -ww` pada man page | bersih |
| Build dua kali (`.deb`, `.tar.gz`, `.zip`, wheel, `PKGBUILD`, `.SRCINFO`) | `SHA256SUMS` identik; `sha256sum -c` OK |
| Fuzz 60.000 input acak pada parser konfigurasi, profil, naskah; 75.000 pada manifest ekstensi, protokol, respons AI, rclone | 0 crash tersisa (3 cacat nyata ditemukan dan diperbaiki: angka non-finite/raksasa pada konfigurasi dan profil, URL API cacat, bentuk respons API aneh; satu temuan lain ternyata positif palsu) |
| Naskah 2 MB (305.000 kata) | statistik dihitung dalam 0,05 dtk |

Catatan menjalankan: tes pengemasan memanggil `python3` dari `PATH`, jadi jalankan dengan venv aktif (`make test`). Tanpa window manager, tes fokus keyboard gagal di Xvfb; gunakan `make test-x11`.

## Cacat yang ditemukan dan diperbaiki (semua punya tes regresi yang terbukti gagal tanpa perbaikannya)

| Cacat | Bukti |
|---|---|
| Mode cermin: `TypeError` pada paint pertama | Dijalankan pada Qt asli; kini identik piksel dengan cermin horizontal pada skala 1×, 1,5×, 2× dan pada Qt 6.8.3 |
| `1e999` / `Infinity` / bilangan raksasa di `config.json` membuat aplikasi crash tiap peluncuran (juga `--diagnostics`); impor profil bernilai sama | Direproduksi dari ujung ke ujung; kini aplikasi mulai dan memakai nilai bawaan |
| Hitung mundur tak terbaca (digambar di atas teks) | Tangkapan layar sebelum/sesudah |
| Halaman Tampilan bergulir ke samping pada jendela bawaan 1100 px (butuh ±1000 px konten) | Diukur: konten 997 → 858 px |
| Alamat API cacat (`http://[`) melempar `ValueError` mentah di UI; respons API berbentuk aneh melempar `KeyError` | Ditemukan fuzz, direproduksi |
| Tes: 3 jenis kesalahan di tes GUI 0.7.0 (versi usang, teardown menggantung oleh dialog tak terjawab, 2 tes hampa), 1 tes pengemasan yang mustahil lulus, 1 tes `drift` rapuh | Dijalankan |
| Dokumentasi: README menyebut `.deb` untuk Ubuntu padahal tidak bisa dipasang di Ubuntu 24.04 | `apt-get install -s` gagal: `python3-pyside6.qtwidgets` tidak ada |
| Segfault acak di Wayland (≈3 dari 10 peluncuran weston baru) | Ditelusuri dengan `gdb` ke race GC Python vs. thread pekerja Qt; `MainThreadGC` memperbaikinya: 0 crash dalam 12 putaran di bawah `gdb`. Tes regresi memastikan `app.main` memasang penjaga (dengan penjaga dilepas, tes gagal) |
| Tanda centang tema bergantung pada plugin SVG Qt yang opsional | Diganti PNG; tes subproses tanpa plugin SVG membandingkan piksel dan gagal bila perbaikan dibatalkan |

## Pengujian di luar suite

| Pengujian | Hasil |
|---|---|
| **Pembaruan nyata**: wheel 0.7.0 yang dibagikan dipasang di venv Python 3.12 → data dibuat (konfigurasi, naskah, profil milikmu) → upgrade ke wheel 0.7.1 | Cadangan otomatis dibuat sebelum menyimpan apa pun; pemberitahuan "baru diperbarui"; naskah, pengaturan, dan profil utuh |
| Rollback: naskah dihapus dan `config.json` dirusak lalu `sorot --restore` cadangan | Keduanya pulih; kondisi sebelum pemulihan disimpan sebagai `…-pre-restore-…zip` |
| `.deb` 0.7.0 yang dibagikan → `.deb` 0.7.1 → `remove` → `purge` (`dpkg`, `--force-depends`) | Skrip maintainer berjalan, versi naik, `remove` dan `purge` bersih |
| `apt-get install -s` `.deb` di Ubuntu 24.04 | **Gagal** (dependensi tidak ada) — hanya Debian 13 yang menyediakannya; didokumentasikan |
| Wheel dipasang di venv Python 3.12 (Ubuntu) | `sorot --version`, `--upgrade-info` berjalan; aset PNG ikut terpasang |
| Overlay di **X11 nyata dengan window manager** (Xvfb + openbox) | `_NET_WM_STATE_ABOVE` aktif; dekorasi mati (Motif hints); posisi dan ukuran sama dengan perhitungan aplikasi; *input shape* kosong saat klik-tembus aktif, penuh saat dimatikan (dibaca langsung dari server X lewat ekstensi SHAPE) |
| Aplikasi penuh (`app.main`) dijalankan 6 dtk di `offscreen` tanpa error di log; hook pembaruan jalan | OK |

## BELUM DIUJI

- **Desktop nyata** (GNOME, KDE, Xfce, Cinnamon) baik Wayland maupun XWayland. Yang sudah dibuktikan di weston headless: aplikasi jalan, overlay tak berbingkai, latar transparan terkomposit (dibaca dari tangkapan compositor), dan 124 tes GUI lulus. Yang tidak dapat dibuktikan di sana: selalu-di-atas, posisi (compositor yang memutuskan), fokus keyboard dan clipboard (tanpa seat).
- **Arch Linux**: `makepkg`, `namcap`, nama paket `pyside6`; job `arch` di CI belum pernah dijalankan. `PKGBUILD` dan `.SRCINFO` hanya diperiksa konsistensi dan reproduktibilitasnya.
- **Mirror Debian dan Arch tidak dapat dijangkau dari lingkungan ini** (kebijakan egress memblokirnya), jadi dua item di bawah tidak dapat diuji di sini apa pun usahanya.
- **Debian 13 bersih lewat `apt`** (dependensi `python3-pyside6.qtwidgets` ada di Debian 13 menurut situs paket Debian, tetapi pemasangan nyata di Debian 13 belum dilakukan; `.deb` hanya dipasang dengan `--force-depends` di Ubuntu) dan menjalankan aplikasi dari paket itu dengan PySide6 dari apt (6.8.2.1).
- **GitHub Actions**: workflow (termasuk job `gui-x11` baru) belum pernah dijalankan; YAML hanya divalidasi sintaksnya.
- Pratinjau di pengaturan (tinggi tetap 112 px) memotong baris pada spasi baris besar; hanya dilihat, tidak dianggap cacat.
- Penyedia AI nyata, rclone/Drive nyata, ekstensi pihak ketiga, keyring nyata, pembaca layar, HiDPI pada layar fisik.
- Pintasan global dan dialog yang membutuhkan interaksi manusia (lihat [MANUAL-TESTING.md](MANUAL-TESTING.md)).

## Cakupan terdahulu
Laporan 0.5.0 dan 0.6.0 tetap menjadi acuan untuk area yang tidak disentuh 0.7.1 (ekstensi, Drive, AI).
