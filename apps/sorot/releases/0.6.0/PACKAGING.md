# Pengemasan dan format distribusi

Sorot adalah Python murni (+ PySide6), jadi satu sumber menghasilkan beberapa format. Semuanya dibangun dari **satu sumber versi** (`src/sorot/__init__.py`), **satu definisi tata letak berkas** (`scripts/install-files.sh`), dan satu tanggal rilis (`packaging/RELEASE_DATE`) sehingga hasil build identik bila diulang.

| Format | Untuk | Dibangun oleh | Status pengujian |
|---|---|---|---|
| `sorot_X_all.deb` | Debian, Ubuntu, dan turunannya | `scripts/build-deb.sh` | Dibangun dan diperiksa struktur isinya; pemasangan pada Debian 13 bersih **BELUM DIUJI** (lihat TEST-REPORT) |
| `PKGBUILD` + `.SRCINFO` + arsip sumber | **Arch Linux** dan turunannya (Manjaro, EndeavourOS, …) | `scripts/build-arch.sh` | Templat dirender dan divalidasi sintaksnya; `makepkg` **BELUM DIJALANKAN** (tidak ada Arch di lingkungan build) |
| `sorot-X-py3-none-any.whl` | pip, pipx, distribusi mana pun | `scripts/build-wheel.sh` | Dibangun; isi diperiksa (termasuk aset SVG) |
| `sorot-X.tar.gz`, `sorot-X.zip` | Sumber; dasar paket distro lain | `scripts/build-source.sh` | Dibangun; dua build identik |
| `install-user.sh` | Pemasangan ke `~/.local` tanpa root | skrip | Diwarisi dari 0.5.0 |
| `make install` | Paket distro lain (Fedora, Nix, Alpine, …) | `Makefile` | Lihat bagian “Distro lain” |

Perintah:

```bash
make help            # daftar target
make release-check   # semua berkas sepakat soal versi/kontak/aset?
make test            # ruff + mypy + pytest
make dist            # semua artefak + SHA256SUMS di dist/
```

## Arch Linux

### Memasang dari rilis

Rilis menyertakan folder `arch/` berisi `PKGBUILD`, `.SRCINFO`, dan `sorot-X.tar.gz` (hash SHA-256 di `PKGBUILD` sudah sesuai arsip itu).

```bash
cd arch
makepkg -si          # membangun, lalu memasang dengan pacman
```

Dari sumber:

```bash
git clone <repositori>  &&  cd sorot      # atau ekstrak sorot-X.tar.gz
scripts/build-arch.sh dist --makepkg      # menghasilkan dist/arch/sorot-X-1-any.pkg.tar.zst
sudo pacman -U dist/arch/sorot-*-any.pkg.tar.zst
```

Menghapus: `sudo pacman -Rns sorot` (data pengguna di `~` tidak disentuh).

### Yang ada di paket

* Dependensi: `python`, `pyside6`. Opsional: `python-keyring`, `rclone`, `qt6-wayland`, `xorg-xwayland`.
* Kode dipasang lewat wheel ke `site-packages` (pedoman Python Arch: `python-build` + `python-installer`); perintah `/usr/bin/sorot` berasal dari entry point.
* Desktop entry, ikon, man page, dokumentasi, contoh ekstensi, lisensi (`/usr/share/licenses/sorot/LICENSE`) lewat `scripts/install-files.sh --layout arch`.
* `check()` menjalankan **hanya tes tanpa GUI** (`-m 'not gui'`) agar pemasangan tidak gagal karena kekhasan desktop. Lewati dengan `--nocheck`.
* Tidak ada `.install` atau hook: pacman sudah memperbarui basis data desktop dan cache ikon sendiri.

### Hal yang perlu diverifikasi di mesin Arch (belum bisa saya lakukan)

1. Nama paket `pyside6` dan bahwa ia sudah menarik semua plugin Qt yang dibutuhkan (xcb).
2. `makepkg -f` selesai tanpa kesalahan, lalu `namcap PKGBUILD` dan `namcap *.pkg.tar.zst`.
3. `sorot --diagnostics` memilih backend yang masuk akal pada sesi Wayland/X11 Arch.
4. Bidang `url=` sengaja kosong karena repositori publik belum ada; isi setelah ada, lalu pertimbangkan mengirimkan ke AUR.

### AUR

Sorot belum diunggah ke AUR. Untuk melakukannya dibutuhkan URL sumber publik yang stabil (rilis GitHub atau serupa): ganti `source=` dengan URL itu, isi `url=`, jalankan `makepkg --printsrcinfo > .SRCINFO`, dan ikuti panduan pengiriman AUR. Templat saat ini memakai arsip lokal supaya bisa dibangun tanpa repositori.

## Distro lain

```bash
scripts/build-wheel.sh dist
python3 -m installer --destdir="$DESTDIR" dist/sorot-*.whl          # kode + perintah `sorot`
scripts/install-files.sh --layout generic "$DESTDIR" /usr           # desktop, ikon, man, doc, lisensi
```

`make install DESTDIR=… PREFIX=/usr` menjalankan keduanya. Kebutuhan runtime: Python ≥ 3.11 dan PySide6 ≥ 6.8.

## Reproduksibilitas

`SOURCE_DATE_EPOCH` diturunkan dari `packaging/RELEASE_DATE`; semua stempel waktu dinormalkan. CI membangun dua kali dan membandingkan `SHA256SUMS`. Hasil di mesin lain bergantung pada versi `dpkg-deb`, `tar`, `gzip`, `xz`, `zip`, dan `setuptools`/`wheel` yang sama.

## Menambah format baru

1. Pakai `scripts/install-files.sh` untuk berkas non-Python; jangan menyalin daftar berkas lagi.
2. Ambil versi dari `scripts/release.py version`.
3. Tambahkan templat di `packaging/<format>/`, skrip `scripts/build-<format>.sh`, sambungkan ke `build-all.sh`, tambahkan pemeriksaan ke `release.py check` dan tes di `tests/test_packaging.py`.
