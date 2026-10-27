# Laporan tes — Sorot 0.7.0 Beta

Tanggal: 2026-10-27 · Lingkungan: Ubuntu 24.04 x86_64, Python 3.12.3, setuptools 68.1.2, wheel 0.42.0, dpkg-deb. **Bukan Debian 13, bukan Arch Linux, bukan sesi desktop nyata.**

> **Batasan penting — baca dulu.** PySide6, pytest, pytest-qt, ruff, mypy, lintian, desktop-file-validate, dan makepkg **tidak tersedia** di lingkungan build ini (tanpa jaringan).
> * Semua kode Qt baru di 0.7.0 — **efek cermin, spasi baris dan spasi huruf, ketebalan huruf, label hitung mundur, panel Profil tampilan di jendela utama** — **belum pernah dijalankan pada Qt asli**. Hanya diperiksa sintaksnya dan diuji logikanya lewat *stub PySide6* (lihat bawah), yang tidak membuktikan bahwa API Qt dipanggil dengan benar atau bahwa hasilnya tampak benar.
> * 11 tes GUI baru sudah ditulis (5 overlay, 6 jendela) tetapi **tidak dijalankan**; bisa saja ada yang gagal.
> * Tes non-GUI dijalankan dengan *runner mini sementara* (bukan pytest asli, bukan bagian rilis).
> * `ruff` dan `mypy` tidak dijalankan; hanya `compileall`.

## Yang dijalankan (runner sementara)

| Pemeriksaan | Hasil |
|---|---|
| `tests/test_profiles.py` (baru, 51 kasus: validasi, penerapan sebagian, JSON, penyimpanan pengguna, tautan simbolik, kontribusi ekstensi, CLI, kunci konfigurasi baru) | lulus |
| `tests/test_upgrade.py` (54), `tests/test_packaging.py` (30), `tests/test_examples.py` (6, termasuk contoh ekstensi bersubproses) | lulus |
| Seluruh tes non-GUI 0.7.0 | **366 lulus, 2 gagal, 57 dilewati** |
| Dua kegagalan | **identik dengan 0.5.0 dan 0.6.0** (runner tidak punya `monkeypatch.syspath_prepend`; satu tes bergantung pustaka sistem) — bukan regresi, tetapi perlu pytest asli |
| `python -m compileall` dan `python3 scripts/release.py check` | bersih / konsisten |

57 kasus dilewati = modul GUI/Qt yang tidak bisa diimpor tanpa PySide6.

### Uji mutasi (kode profil)
Kunci dirusak sementara dan tes harus gagal: kunci non-tampilan lolos ✔ (tertangkap, tetapi hanya satu kasus karena ada lapis pertahanan kedua yang tetap menyaringnya), penerapan profil mereset kunci yang tidak tercantum ✔, nama profil bawaan bisa ditimpa ✔, tautan simbolik diikuti ✔, versi format tidak diperiksa ✔. Satu mutasi (batas ukuran di `loads`) **lolos** karena tes hanya menyentuh `read_file`; tes ditambahkan dan kini menangkapnya.

Dua kesalahan di tes saya sendiri yang ditemukan lewat proses ini: `"ya"` ternyata nilai boolean yang sah (`_to_bool`), dan satu tes GUI akan salah karena profil “Kertas terang” tidak mencantumkan `letter_spacing` (diganti memakai `font_size`).

### Uji asap dengan stub PySide6
Modul PySide6 palsu yang permisif memungkinkan `ui.main_window`, `overlay`, `widgets`, `appearance` **di-import** dan metode `_refresh_profiles`, `_matching_profile`, `_sync_profile_combo`, `_on_profile_chosen`, `_save_profile`, `_export_profile`, `_import_profile`, `_delete_profile`, `_countdown_tick`, `_cancel_start_delay`, `_delayed_start` dijalankan dengan widget tiruan terhadap kode profil asli. Hasilnya benar (profil diterapkan/disimpan/diekspor/diimpor/dihapus; hitung mundur turun dan dibersihkan). Ini menangkap salah ketik dan kesalahan logika; **bukan** pengganti tes Qt.

## Pengujian di luar suite

| Pengujian | Hasil |
|---|---|
| `dpkg -i` `sorot_0.6.0_all.deb` lalu `sorot_0.7.0_all.deb` (`--force-depends`) dengan data pengguna 0.6.0 bersistem skema 3 | 0.7.0 menggantikan 0.6.0; `--upgrade-info` mengenali “diperbarui dari 0.6.0”, skema di disk 3 / didukung 4; `--profiles`, `--export-profile`, `--import-profile` bekerja; profil milikmu masuk ke `--backup`; berkas `config.json` lama tidak diubah |
| Build dua kali (`.deb`, `.tar.gz`, `.zip`, wheel, `PKGBUILD`, `.SRCINFO`) | `SHA256SUMS` identik; `sha256sum -c` OK |

## BELUM DIUJI

- **Semua tampilan Qt baru** (lihat di atas): apakah `FlipEffect` benar-benar membalik teks pada overlay transparan, apakah hasilnya benar di Wayland/X11/compositor tertentu, apakah `setLineHeight` memberi hasil yang diharapkan dan timeline gulir tetap akurat dengan spasi baris besar, apakah label hitung mundur tampak dan terbaca, dan tata letak panel Profil tampilan.
- Mode cermin hanya membalik tampilan: input mouse pada teks tidak dibalik (tidak relevan untuk teks baca-saja, tetapi belum dicoba).
- Pratinjau di pengaturan: tinggi tetap 112 px; belum diperiksa apakah spasi baris besar terpotong.
- Pintasan, jendela utama penuh (`app.main`) dan hook pembaruan saat aplikasi berjalan penuh, pemberitahuan cadangan otomatis di jendela, dialog Tentang → Kontak.
- **Arch Linux**: `makepkg`, `namcap`, nama paket `pyside6`; job `arch` di CI belum pernah dijalankan.
- `ruff`, `mypy`, `lintian`, `desktop-file-validate`; instalasi `.deb` via apt di Debian 13 bersih.
- Yang sudah tercantum BELUM DIUJI pada laporan 0.5.0 (compositor nyata, penyedia AI, rclone/keyring, ekstensi pihak ketiga, GitHub Actions, pembaca layar).

## Cakupan terdahulu
Laporan 0.5.0 (378 lulus dengan pytest + PySide6 + ruff + mypy) dan 0.6.0 menjadi acuan untuk area yang tidak disentuh 0.7.0.
