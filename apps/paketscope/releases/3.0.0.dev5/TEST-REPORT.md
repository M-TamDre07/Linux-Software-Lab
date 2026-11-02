# Laporan tes — PaketScope 3.0.0.dev5 (pratinjau pengembangan)

Status rilis: **testing** (bukan stable). Dukungan: **Debian 13, terbatas**. Arch dan Fedora: **tidak didukung**.

## Batasan penting — baca dulu

- Lingkungan build: Ubuntu 24.04 x86_64, Python 3.12, PySide6 6.12.0, pytest 9.2. **Bukan Debian 13, bukan Arch Linux, bukan Fedora, bukan sesi desktop nyata.**
- PaketScope mengimplementasikan operasi paket hanya untuk APT/dpkg. Di Arch dan Fedora, inventori dan aksi paket akan melaporkan alat yang tidak tersedia.
- Validasi instalasi paket `.deb` dilakukan oleh GitHub Actions pada container Debian 13 (Trixie) terisolasi: paket dibangun, diperiksa, dipasang lewat APT dengan resolusi dependensi, modul Python berhasil diimpor, lalu paket di-purge. Ini membuktikan alur packaging pada image CI tersebut, bukan pengujian desktop fisik.
- Discover belum diuji menampilkan aplikasi dari repositori (memerlukan metadata DEP-11 dari `appstream-generator` di server).

## Bukti CI Debian 13 — 2 November 2026

Workflow PaketScope build menjalankan job **Build, install, and purge on Debian 13** dan berakhir sukses pada commit integrasi. Log menunjukkan paket `3.0.0~dev5-1` dibangun dengan debhelper, metadata paket dibaca, APT memasang dependensi pada Debian 13/Trixie, status dpkg menjadi `install ok installed`, dan modul `paketscope` versi `3.0.0.dev5` dapat diimpor dari `/usr/lib/python3/dist-packages`. Job kemudian menjalankan purge dan menyimpan artefak CI pengembangan.

Matriks tes sumber pada Python 3.10, 3.11, 3.12, dan 3.13 juga lulus pada workflow yang sama. Validasi ini tidak membuktikan interaksi Polkit yang memerlukan pengguna, GNOME/KDE desktop nyata, aksesibilitas, Discover/DEP-11, repositori APT produksi, atau tanda tangan kunci rilis milik pengelola.

## Yang dijalankan dan hasilnya

| Pemeriksaan | Hasil |
|---|---|
| `pytest` pada sumber (PySide6 6.12, offscreen), 3 run berurutan | 92 lulus setiap run, 0 gagal, 3 peringatan |
| `ruff check` | 12 temuan tersisa (gaya dan `BLE001`/`B008`); 0 temuan yang mengubah perilaku |
| `mypy paketscope` | 76 error, sebagian besar tipe mixin UI (`attr-defined`, `arg-type`). **Utang tipe, belum dibersihkan.** |
| `lintian --fail-on error` pada `.deb` | Lulus (exit 0). Peringatan: panjang baris changelog, tidak ada man page |
| `appstreamcli validate --no-net` pada metainfo | "Validation was successful" |
| GUI dari layout `.deb` (offscreen, 12 detik) | Event loop berjalan, 0 traceback |
| Modul terpasang | Versi `3.0.0.dev5` |
| Pembaruan di tempat `dev4` → `dev5-1`, dpkg root terisolasi | `install ok installed`, file lengkap, modul versi baru |
| Repositori APT bertanda tangan (kunci uji), apt terisolasi | Kandidat `3.0.0~dev5-1` terlihat, tanda tangan "Good signature" |
| Simulasi `apt upgrade` dev4 → dev5 (dependensi ditandai terpenuhi) | `Inst paketscope [3.0.0~dev4] (3.0.0~dev5-1 ...)` |
| RPM Fedora, uji struktur (sitelib diberikan manual) | Dibangun; instal dan copot bersih, 0 sisa |
| PKGBUILD Arch | Sintaks OK; `package()` menghasilkan tata letak lengkap |
| Wheel `pip wheel --no-deps` | Dibangun (versi PEP 440 valid) |

## Perbaikan dalam rilis ini (dibanding dev4)

1. **Versi PEP 440.** `3.0.0.dev4.1` sempat dipakai, dan itu tidak valid: `pip`/wheel gagal membangun proyek. Diganti `3.0.0.dev5`.
2. **Flatpak branch.** Nilai branch di-parse lalu dibuang, tidak pernah sampai ke detail aplikasi. Sekarang ada field `branch`.
3. **Metadata AppStream dan profil pengembang** untuk Discover dan `apt show`.
4. **Pembersihan ruff otomatis** (urutan import, konkatenasi string). Tanpa `--unsafe-fixes`.

## Keterbatasan yang diketahui

- `mypy` masih 76 error di modul UI. Ini utang tipe, bukan bukti bug, tetapi belum diverifikasi per kasus.
- Blok `except Exception` di `collectors.py` dan `ui/workers.py` disengaja untuk mengisolasi sumber data gagal. Tetap perlu ditinjau.
- Tes GUI berjalan offscreen. Interaksi nyata (klik, dialog polkit, `pkexec`) belum diuji di sesi desktop.

## Syarat sebelum status bisa menjadi "stable"

1. Ulangi instal, jalankan, perbarui, dan copot pada Debian 13 bersih di VM/mesin pengguna, serta verifikasi hasilnya di luar image CI.
2. Tes GUI dijalankan di Qt asli dengan interaksi (pemilihan paket, pratinjau APT, konfirmasi).
3. `mypy` dan `ruff` bersih, atau setiap temuan tersisa dicatat dengan alasan.
4. Repositori di-hosting dan kunci rilis dikelola pemilik, bukan kunci uji.
5. Tidak ada temuan kritis terbuka dalam tinjauan keamanan operasi APT (pkexec, validasi argumen).

Sampai syarat itu terpenuhi, rilis ini berstatus **testing**.
