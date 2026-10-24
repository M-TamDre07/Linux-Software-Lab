# Sorot — dukungan distribusi Linux

Dokumen ini membedakan **artefak yang benar-benar tersedia** dari target packaging berikutnya. Nama distro di daftar ini bukan klaim bahwa seluruh sesi desktop telah diuji.

## Status artefak

| Format / distribusi | Status | Catatan |
| --- | --- | --- |
| Debian package (.deb) | Tersedia untuk beta | `sorot_0.5.0_all.deb`; pengujian yang tercatat dilakukan di Ubuntu 24.04. Instalasi bersih Debian 13 dan resolusi dependensinya belum diverifikasi dalam laporan tes. |
| Ubuntu 24.04 | Lingkungan uji tercatat | Ini menjelaskan lingkungan tes, bukan jaminan untuk semua versi Ubuntu atau desktop environment. |
| Debian 13 | Belum terverifikasi penuh | Jangan menyimpulkan kompatibilitas instalasi hanya dari ekstensi .deb. |
| Arch Linux / Arch-based | Belum tersedia | Belum ada PKGBUILD yang dibangun dan diuji. |
| Fedora / RPM-based | Belum tersedia | Belum ada spec RPM yang dibangun dan diuji. |
| Flatpak | Belum tersedia | Belum ada manifest yang diverifikasi dengan Flatpak Builder dan portal runtime. |
| AppImage | Belum tersedia | Belum ada AppImage yang dibangun dan diuji pada sistem target. |

## Rencana packaging

Sebelum menambahkan format baru, packaging harus dibuat dari source yang sama dengan rilis Sorot dan tidak mengubah artefak 0.5.0 yang sudah ada.

1. **Inventarisasi source build** — pastikan entry point, dependency runtime, data files, desktop entry, icon, lisensi, dan lokasi data pengguna dari source archive.
2. **Arch Linux** — tulis PKGBUILD dengan dependency runtime eksplisit, source checksum yang dipatok, pemisahan build/runtime dependency, serta validasi `namcap` dan pemasangan pada VM Arch bersih.
3. **RPM** — buat spec yang sesuai dengan dependency Fedora dan lokasi file standar; validasi build RPM serta instal/uninstall di Fedora bersih.
4. **Flatpak** — buat manifest dengan source commit/hash tetap, dependency build yang dipatok, izin minimum, dan pengujian sandbox/portal. Jangan memberi izin jaringan atau filesystem luas tanpa kebutuhan yang terdokumentasi.
5. **AppImage** — tentukan strategi bundling PySide6/Qt dan plugin platform; uji pada host Linux berbeda dan verifikasi bahwa paket tidak bergantung pada library host yang tidak terdokumentasi.
6. **Validasi bersama** — uji instalasi, peluncuran, upgrade, uninstall, ikon/desktop entry, lokasi konfigurasi pengguna, dan perilaku overlay di Wayland/X11. Catat distro, versi, arsitektur, compositor, dan hasilnya di laporan rilis.

## Kriteria klaim dukungan

Jangan ubah status distribusi menjadi “didukung” hanya karena file packaging berhasil dibuat. Status harus menunggu build bersih dan pengujian install/run/uninstall pada versi distro dan arsitektur yang dinyatakan. Setiap artefak publik perlu checksum SHA-256 dan instruksi verifikasi.

Ekstensi kode Sorot berjalan dalam proses terpisah tetapi bukan sandbox keamanan; packaging Flatpak tidak boleh dipasarkan sebagai jaminan bahwa ekstensi kode di dalam aplikasi otomatis terisolasi dari semua akses.
