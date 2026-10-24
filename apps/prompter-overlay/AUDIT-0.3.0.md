# Laporan audit 0.3.0

Materi yang diterima: **hanya** `tama-prompter_0_3_0_all.deb` (nama berkas unggahan). Tidak ada repositori, direktori `src/`, `tests/`, `.github/`, `docs/`, `install-user.sh`, atau `build-deb.sh`. Kode yang diaudit adalah kode di dalam paket (`/usr/lib/tama-prompter`, 14 berkas Python, ±75 KB) dan perilakunya dijalankan dengan Qt `offscreen` (PySide6 6.12.0, Python 3.12.3).

Kondisi awal terverifikasi: aplikasi dibuat, overlay tampil, gulir berjalan, jeda dan klik-tembus (flag jendela) bekerja, penutupan bersih — pada Qt offscreen saja.

## Temuan

| ID | Tingkat | Temuan | Bukti | Status |
|---|---|---|---|---|
| A1 | Tinggi | README menyebut tes unit, CI, `docs/COMPATIBILITY.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md`, `install-user.sh`, `build-deb.sh`, tetapi tidak satu pun ada dalam materi. Klaim “tes unit dan build paket dapat dijalankan otomatis” tidak dapat diverifikasi. | Isi paket | Dibangun ulang; klaim lama tidak dipakai |
| A2 | Tinggi | Posisi overlay manual (`overlay_x/y`) disimpan tetapi `_load_preferences` tidak membacanya → posisi hilang setelah restart. | Kode; konfigurasi awal menunjukkan kunci tersimpan | Diperbaiki + tes regresi |
| A3 | Tinggi | `setPlainText` untuk mengganti naskah menghapus undo; membuka berkas/Drive menimpa editor tanpa konfirmasi; tidak ada pelacakan perubahan atau peringatan saat keluar. | Kode | Diperbaiki + 6 tes |
| A4 | Tinggi | Geser overlay memakai `move()` manual: tidak bekerja pada Wayland asli. | Kode + dokumentasi Qt | Diganti `startSystemMove/Resize` (efek di compositor nyata **BELUM DIUJI**) |
| A5 | Tinggi (keamanan) | `urllib` mengikuti redirect dan meneruskan header `Authorization` ke host tujuan. | Perilaku default urllib | Redirect ditolak; tes dengan dua server lokal membuktikan key tidak diteruskan |
| A6 | Sedang | Permintaan AI tak dapat dibatalkan; dialog tidak dapat ditutup selama berjalan (hingga 120 dtk); `QThreadPool` menunggu tugas saat keluar. | Kode | Thread daemon + pembatalan kooperatif + tes |
| A7 | Sedang | Mencentang-ulang “simpan di keyring” menjadi tidak dicentang menghapus key tersimpan tanpa pemberitahuan. | Kode | Diganti tombol hapus eksplisit |
| A8 | Sedang | Seluruh naskah dan pengaturan dalam satu berkas QSettings tak terenkripsi, ditulis ulang setiap perubahan; tanpa versi skema, tanpa penanganan berkas rusak, tanpa pemulihan crash selain itu. | Kode + README lama (mengakui tidak terenkripsi) | JSON berversi, atomik, draf terpisah 0600, karantina berkas rusak, migrasi non-destruktif |
| A9 | Sedang | Tidak ada logging sama sekali; kegagalan keyring ditelan (`except Exception: return ""`). | Kode | Logging + penyamaran rahasia |
| A10 | Sedang | Logika backend ganda (launcher shell dan Python); xcb dipaksa pada Wayland bila `DISPLAY` ada walau plugin xcb tidak terpasang → Qt abort tanpa pesan; nilai `TAMA_QT_PLATFORM` tak valid diabaikan diam-diam. | Kode | Satu fungsi murni yang diuji; plugin diperiksa |
| A11 | Sedang | Drive: `rclone cat` tanpa batas ukuran sebelum diperiksa; `lsf` menelusuri seluruh remote tanpa batas kedalaman; daftar sampai 1000 berkas dalam `QInputDialog`; tak dapat dibatalkan; semua remote dianggap Drive. | Kode | Dibatasi, dapat dibatalkan, disaring, remote bertipe |
| A12 | Sedang | Teks overlay diset ulang penuh pada setiap ketikan (O(n)). | Kode | Debounce 150 ms |
| A13 | Rendah | `User-Agent` memakai versi yang di-hardcode; versi tersebar di banyak tempat. | Kode | Satu sumber versi |
| A14 | Rendah | Paket tanpa `md5sums`, changelog, man page, skrip maintainer, kategori `.desktop` tidak valid. | Isi paket | Ditambahkan; `lintian` dijalankan |
| A15 | Rendah | Fitur diminta tetapi tak ada: jenis huruf, perataan, margin, selalu-di-atas, mode tanpa bingkai, ubah ukuran, pratinjau, pintasan dapat diatur, tombol di overlay, uji koneksi AI, tugas durasi/formal/santai. | UI | Ditambahkan |
| A16 | Rendah | Maintainer `maintainer@tama-prompter.invalid` adalah placeholder. | control | **Dibiarkan** (tidak boleh mengarang kontak); hambatan rilis publik |
| A17 | Info | `Architecture: all` sudah benar (Python murni). Dependensi PySide6 untuk Debian 13 tidak dapat diverifikasi di lingkungan Ubuntu. | — | Dipertahankan, ditandai belum diverifikasi |

Tidak ditemukan: API key di source, TODO/placeholder fungsional, `shell=True`, atau fitur berupa mock. Kode Drive memang memakai argumen list.
