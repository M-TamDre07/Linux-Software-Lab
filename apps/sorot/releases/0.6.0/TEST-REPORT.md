# Laporan tes — Sorot 0.6.0 Beta

Tanggal: 2026-10-26 · Lingkungan: Ubuntu 24.04 x86_64, Python 3.12.3, setuptools 68.1.2, wheel 0.42.0, dpkg-deb. **Bukan Debian 13, bukan Arch Linux, bukan sesi desktop nyata.**

> **Batasan penting.** Di lingkungan build kali ini **PySide6, pytest, pytest-qt, ruff, mypy, lintian, desktop-file-validate, dan makepkg tidak tersedia** (tanpa akses jaringan). Karena itu:
> * Tes non-GUI dijalankan dengan *runner mini sementara* yang meniru bagian kecil pytest (`tmp_path`, `monkeypatch`, `capsys`, `parametrize`, `raises`); runner itu **bukan bagian rilis**. Hasilnya belum menggantikan `pytest` asli.
> * **Seluruh tes GUI (±5 berkas, termasuk tes dialog Tentang yang baru) tidak dijalankan.** Hasil 378 lulus pada laporan 0.5.0 **tidak berlaku otomatis** untuk 0.6.0.
> * `ruff` dan `mypy` tidak dijalankan; hanya `compileall` (sintaks).

## Yang dijalankan (runner sementara)

| Pemeriksaan | Hasil |
|---|---|
| `tests/test_upgrade.py` (baru, 53 kasus) | lulus |
| `tests/test_packaging.py` (baru, 30 kasus; membangun `.deb`, arsip sumber, wheel, dan paket Arch dua kali) | lulus |
| `tests/test_support.py` (diperluas: kontak/email) | lulus |
| Seluruh tes non-GUI 0.6.0 | **313 lulus, 2 gagal, 57 dilewati** |
| Pembanding: tes yang sama pada pohon 0.5.0 asli | 221 lulus, **2 gagal yang sama**, 57 dilewati |
| `python -m compileall src tests scripts/release.py` | bersih |
| `python3 scripts/release.py check` | konsisten |

Dua kegagalan yang ada **juga pada 0.5.0 asli** dan bukan regresi: `test_pip_installed_extensions_are_found_through_entry_points` (runner tidak punya `monkeypatch.syspath_prepend`) dan `test_plugin_with_missing_dependency_is_not_offered` (bergantung pada pustaka sistem di lingkungan ini). Keduanya perlu dijalankan ulang dengan pytest asli.

57 kasus dilewati = modul GUI/Qt yang tidak bisa diimpor tanpa PySide6.

### Uji mutasi (kode yang baru)
Perilaku kunci dirusak sementara dan tes harus gagal: hash cadangan tidak diperiksa ✔, pemulihan tetap jalan saat aplikasi aktif ✔, cadangan pengaman sebelum pemulihan dilewati ✔, pemangkasan otomatis ikut menghapus cadangan manual ✔, pembaruan dari rilis tanpa catatan versi tidak dicadangkan ✔, pemeriksaan `..` pada nama berkas ✔, pemeriksaan nama kanonik ✔, pengurungan tujuan tulis ✔.

Dua temuan dari proses ini (sudah diperbaiki): mutasi pertama pada pemeriksaan `..` **lolos** karena tesku menolak nama itu lewat hash yang salah, bukan lewat validasi nama — tes diperbaiki memakai hash benar; dan nama seperti `config/./x` ternyata diterima karena `PurePosixPath` menormalkan `.` secara diam-diam — validasi kini menolak nama tidak kanonik.

## Pengujian di luar suite

| Pengujian | Hasil |
|---|---|
| `dpkg -i` `sorot_0.5.0_all.deb` (berkas unggahan asli) lalu `sorot_0.6.0_all.deb` (dengan `--force-depends` karena PySide6 tidak ada) | 0.6.0 menggantikan 0.5.0 di `/usr/lib/sorot`; `sorot --version` = 0.6.0; `--upgrade-info` mengenali “Paket Debian/Ubuntu”; `--backup`/`--restore` bekerja pada data contoh; `dpkg -r` membersihkan `/usr/lib/sorot` dan data pengguna tetap utuh |
| Build dua kali (`.deb`, `.tar.gz`, `.zip`, wheel, `PKGBUILD`, `.SRCINFO`) | `SHA256SUMS` identik |
| `sha256sum -c SHA256SUMS` | semua OK |
| Isi wheel | memuat `check-dark.svg`/`check-light.svg`, `core/upgrade.py`, entry point `sorot = sorot.app:main`; **wheel 0.5.0 tidak memuat SVG** (dikonfirmasi sebelum perbaikan) |
| `bash -n` pada semua skrip dan `PKGBUILD` yang dirender; evaluasi array `PKGBUILD` oleh bash dibandingkan dengan `.SRCINFO` | cocok |
| Tata letak `install-files.sh` untuk `deb`/`arch`/`generic` | lulus (izin 0644, tidak menulis di luar DESTDIR) |

## BELUM DIUJI

- **Arch Linux sama sekali**: `makepkg`, `namcap`, nama paket `pyside6`, `pacman -U/-Rns`, jalan pada desktop Arch. Job `arch` di CI disiapkan tetapi belum pernah dijalankan. `.SRCINFO` dibuat oleh generator sendiri (urutan barisnya berbeda dari keluaran `makepkg --printsrcinfo`; di Arch yang terakhir dipakai otomatis).
- `make install` (butuh `python-installer`, tidak ada di sini) dan `scripts/install-user.sh` (butuh PyPI).
- **Tes GUI** dan jalur `app.main` yang membuka jendela, termasuk tampilnya pemberitahuan cadangan otomatis di jendela utama dan dialog Tentang → Kontak. Hook `upgrade.on_startup` diuji sebagai unit, tetapi **belum dipanggil dari aplikasi yang berjalan penuh**.
- `ruff`, `mypy`, `lintian`, `desktop-file-validate` (paket `.deb` baru belum di-lint).
- Instalasi `.deb` di Debian 13 bersih dengan dependensi PySide6 sungguhan; apt (bukan `dpkg -i`).
- Semua yang sudah tercantum BELUM DIUJI pada laporan 0.5.0: compositor Wayland/X11 nyata, penyedia AI, rclone/keyring nyata, ekstensi pihak ketiga, workflow GitHub Actions, pembaca layar.

## Cakupan 0.5.0 (tidak diulang)
Laporan 0.5.0 (378 lulus dengan pytest + PySide6 6.12.0, ruff, mypy, lintian pedantic) tetap menjadi acuan untuk area yang tidak disentuh 0.6.0: mesin gulir, overlay, ekstensi, AI/Drive. Perubahan 0.6.0 pada kode lama hanya: refaktor `upgrade_schema` menjadi registri (perilaku identik, dibuktikan tes rantai migrasi), `app.py` (opsi CLI + hook), `ui/dialogs.py` (bagian kontak), dan `support.py` (validasi email).
