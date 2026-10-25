# Laporan tes — Sorot 0.5.0 Beta

Tanggal: 2026-10-18 · Lingkungan: Ubuntu 24.04 x86_64, Python 3.12.3, PySide6 6.12.0, pytest 9.1.1, pytest-qt 4.5.0.
**Bukan Debian 13 dan bukan sesi desktop nyata.**

## Ringkasan

| Pemeriksaan | Hasil |
|---|---|
| `ruff check src tests` | lulus |
| `mypy src` (43 berkas) | tanpa masalah |
| `pytest` | **378 lulus, 0 gagal, 0 dilewati** (±92 dtk) |
| `lintian --pedantic` | 1 catatan pedantic (`repeated-path-segment`, wajar untuk direktori privat Python); tanpa error/warning |
| `desktop-file-validate` | bersih |
| Build dua kali menghasilkan checksum identik (deb, tar.gz, zip) | ya |

## Cakupan

| Area | Jenis tes | Yang diperiksa |
|---|---|---|
| Inti tanpa Qt (config v3 + migrasi skema, naskah/draf/snapshot, fileio, redaksi, statistik, model waktu) | unit | validasi dan penjepitan nilai, berkas rusak dikarantina, snapshot (dedupe/throttle/prune/jalur aman), tanda baca dan isyarat memengaruhi durasi |
| Markup naskah dan timeline | unit | `//` catatan, `[jeda N]` (varian, penjepitan, tiruan teks biasa), pemetaan 1:1 baris, mode kata/menit, durasi target (tepat sasaran, jeda dipertahankan), piksel/detik, monoton, invers `time_at`, batas kecepatan |
| AI, Drive, platform | unit + integrasi (server HTTP palsu, rclone palsu) | klasifikasi error, redirect tidak diikuti dan key tidak diteruskan, timeout/batal, argumen rclone sebagai list, validasi jalur, pilihan backend, tabel kemampuan |
| Overlay (jam palsu) | GUI offscreen | start/stop halus, kecepatan tak bergantung laju tick, jeda isyarat menahan layar, selesai/ulang, scrub manual menyinkronkan jam, ganti kecepatan menjaga posisi, mode durasi, tidak rekursi pada naskah kosong |
| Jendela utama | GUI offscreen | persistensi, posisi manual, draf/crash, peringatan perubahan, buka/simpan, undo, pintasan, mode kecepatan, tidak ada peringatan “belum disimpan” palsu |
| Ekstensi — manifest, penemuan, pemasang | unit | id/API/entry tak aman, entri tak valid dibuang, hash kode, zip-slip, simlink, zip bomb, uninstall terkurung, entry point pip |
| Ekstensi — host (subprocess nyata) | integrasi | hello/capabilities, transform/impor/ekspor/aksi, naskah 1 MB, exception dan stdout liar tidak merusak protokol, env dibersihkan dari API key, timeout membunuh proses, crash, pembatalan, event hanya ke pelanggan, restart, kegagalan beruntun vs sesekali |
| Ekstensi — end-to-end lewat jendela | GUI + subprocess | kode tidak jalan sebelum disetujui, persetujuan bertahan restart tetapi dicabut saat kode berubah, transformasi pada seleksi dan undo, hasil dibuang bila naskah berubah, batal, impor/ekspor, event, halaman Ekstensi (pasang folder/ZIP, hapus, sistem tak bisa dihapus), tema/preset/templat/tugas AI |
| Dukungan, instance tunggal, crash | unit + GUI | nomor dinormalisasi, hanya https, dialog tidak muncul sendiri, tidak ada akses jaringan sebelum klik, kunci instance dan kunci basi, pengecualian dicatat tanpa rahasia |
| Contoh ekstensi | integrasi | ketiga contoh valid dan benar-benar berjalan |

### Uji mutasi
Perilaku kunci dirusak sementara dan tes terkait harus gagal: persetujuan tidak terikat hash ✔, ekstensi berjalan sebelum disetujui ✔, hasil lama menimpa ketikan ✔, lingkungan ekstensi membocorkan variabel ✔, jeda isyarat tidak menahan ✔, penanda “belum disimpan” palsu ✔. Satu mutasi (pemeriksaan zip-slip tahap pertama dimatikan) tidak terdeteksi **karena ada lapis pertahanan kedua** yang menolak jalur yang sama; keduanya dipertahankan.

### Bug yang ditemukan tes selama pengerjaan (semua sudah diperbaiki)
Rekursi tak terbatas di overlay (naskah kosong + mode durasi) · interval tick negatif · peringatan “belum disimpan” palsu setelah mewarnai markup · restart ekstensi memakai antrean tulis lama (hello tertelan) · penghitung restart yang tak pernah di-reset · cache palet tema tidak diperbarui · `busy()` ekstensi berubah False sebelum hasil diterapkan · lebar minimum jendela terlalu besar.

## Pengujian di luar suite

| Pengujian | Hasil |
|---|---|
| `dpkg -i` paket lama `tama-prompter` 0.4.0 lalu `sorot` 0.5.0 | `tama-prompter` dihapus otomatis (Conflicts/Replaces), `sorot` terpasang |
| `sorot --version`, `--extensions` dari paket terpasang; `dpkg -r`, `dpkg -P` | berhasil; `/usr/lib/sorot` bersih setelah hapus |
| Tangkapan layar tema gelap dan terang (Qt offscreen), dua perbaikan visual dari temuan ini | dilakukan |
| Impor dari instalasi 0.4.x dan berkas 0.3.x (diuji pada versi sebelumnya dan lewat tes unit/GUI) | berhasil, berkas lama tidak diubah |

Catatan lingkungan: sandbox ini meng-exclude `/usr/share/doc` dan man page pada `dpkg`, jadi berkas dokumentasi dan contoh di dalam paket tidak terlihat setelah pemasangan di sini. Keberadaannya di dalam `.deb` sudah diperiksa lewat `dpkg-deb -c`.

## BELUM DIUJI

- Sesi nyata GNOME Wayland, KDE Plasma (overlay: selalu-di-atas, klik-tembus, geser/ubah ukuran, multi-monitor, layar penuh), Xfce, Cinnamon. Prosedur: [source ZIP 0.5.0](sorot-0.5.0.zip) (file MANUAL-TESTING.md is inside the source archive). (Laporan pengguna untuk 0.4.0: aplikasi berjalan di Debian 13 KDE Wayland via XWayland dengan PySide6 6.8.2.1 dan Python 3.13.5.)
- Instalasi `sorot_0.5.0_all.deb` di Debian 13 bersih dan penyelesaian dependensinya; suite tes pada PySide6 6.8.x dan Python 3.11/3.13.
- Penyedia AI nyata, rclone/Google Drive nyata, keyring nyata (hanya test double lokal).
- Ekstensi pihak ketiga sungguhan; ekstensi bukan sandbox dan tidak diuji terhadap kode yang berniat jahat selain pemeriksaan manifest, jalur, hash, env, dan timeout.
- Workflow GitHub Actions (belum pernah dijalankan); aksesibilitas dengan pembaca layar.
