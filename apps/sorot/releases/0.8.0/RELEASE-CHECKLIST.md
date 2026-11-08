# Checklist rilis

Bagian otomatis dijalankan oleh `make release-check` (dan oleh tes `tests/test_packaging.py`); yang tersisa adalah hal yang hanya bisa diputuskan atau diuji manusia di mesin nyata.

## Otomatis (jangan dicentang manual)

```bash
python3 scripts/release.py bump X.Y.Z --date YYYY-MM-DD   # satu perintah untuk semua nomor versi
make release-check test                                    # versi, changelog, tanggal, kontak, aset, placeholder
make dist                                                  # .deb, wheel, sumber, arch/, SHA256SUMS
```

`release-check` memastikan: `__version__` = `VERSION_LABEL` = changelog teratas = changelog Debian = README = PKGBUILD; tanggal rilis valid dan cocok; tidak ada `TODO` di entri teratas; kontak resmi ada di metadata; tidak ada alamat `*.invalid`; setiap aset UI tercakup `package-data`.

## Manual

- [ ] Isi entri `CHANGELOG.md` dan `packaging/debian-changelog` (kata `TODO` membuat `check` gagal)
- [ ] Jika skema pengaturan naik: langkah baru di `MIGRATIONS` + tes; jika format cadangan berubah: tetap baca format lama
- [ ] Perbarui `docs/UPGRADING.md` bila jalur versi atau perilaku pembaruan berubah
- [x] `Source:`, `Homepage:`, `url=`, metainfo dan `pyproject` sudah memakai alamat repositori (dijaga `release.py check`)
- [ ] Aktifkan *Private vulnerability reporting* di tab Security repositori GitHub, lalu perbarui `SECURITY.md`
- [ ] Pastikan lisensi: akar repositori berlisensi GPL-3.0 sedangkan Sorot MIT; letakkan `apps/sorot/LICENSE` (MIT) dan nyatakan lisensi per aplikasi di README repositori
- [ ] CI GitHub Actions hijau (matriks Python 3.11/3.12/3.13, job `gui-x11`, `package`, dan Arch) — workflow belum pernah dijalankan; semua langkahnya sudah dijalankan manual secara lokal (lihat [TEST-REPORT.md](TEST-REPORT.md))
- [ ] **Debian 13 bersih** (bukan Ubuntu: `.deb` tidak dapat dipasang di Ubuntu 24.04): `apt install ./sorot_X_all.deb`, jalankan, `remove` dan `purge`; periksa dependensi `python3-pyside6.qtwidgets` dan apakah tanda centang tema (PNG) tampil; siklus `dpkg` dengan `--force-depends` sudah dijalankan di Ubuntu
- [ ] **Arch Linux bersih** (mis. `archlinux:base-devel` atau VM): `makepkg -si` dari `dist/arch`, `namcap PKGBUILD` dan `namcap *.pkg.tar.zst`, jalankan, `pacman -Rns`
- [ ] **Skenario pembaruan nyata di desktop**: sudah dijalankan lewat CLI/wheel (0.7.0 → 0.7.1, lihat TEST-REPORT); ulangi dengan aplikasi yang berjalan penuh di desktop nyata
- [ ] [Pengujian manual](MANUAL-TESTING.md) minimal baris 1 dan 3; perbarui `docs/COMPATIBILITY.md`
- [ ] **Wayland** (GNOME dan KDE) dan **compositor nyata**: overlay transparan, selalu-di-atas, klik-tembus, dan **mode cermin** terlihat benar di layar fisik / beam-splitter; yang sudah diverifikasi hanya X11 tanpa compositor dan Wayland di weston headless
- [ ] Uji integrasi Drive dengan rclone asli dan akun uji; uji AI dengan satu penyedia nyata
- [ ] Uji ekstensi contoh pada desktop nyata dan pasang satu ekstensi dari ZIP
- [ ] Konfirmasi nomor GoPay (`src/sorot/support.py`), tautan Saweria, dan alamat email kontak benar; sadari semuanya menjadi publik di repositori dan paket
- [ ] Periksa nama “Sorot” belum dipakai produk lain di bidang yang sama (pemeriksaan merek dagang belum dilakukan)
- [ ] Tag git, unggah artefak + `SHA256SUMS` — **hanya setelah persetujuan eksplisit pemilik**

## Tambahan 0.8.0 (tindakan pengelola)
- [ ] Simpan `dist/latest.json` (`make update-manifest BASE=…`) sebagai `apps/sorot/latest.json` hanya setelah berkas rilis diunggah dan hash cocok
- [ ] Di Fedora nyata: `make rpm` tanpa `RPM_NODEPS`, `sudo dnf install`, jalankan, `rpmlint`
- [ ] Di mesin dengan Flatpak: `scripts/build-flatpak.sh --build`, jalankan, lalu ajukan ke Flathub (konfirmasi ID aplikasi)
- [ ] Buka berkas `.docx`, `.odt`, `.pdf` milikmu sendiri lewat Buka dan seret-lepas; periksa hasilnya
- [ ] Bantuan → Periksa pembaruan: harus menampilkan "Belum ada informasi pembaruan" sebelum `latest.json` diterbitkan
