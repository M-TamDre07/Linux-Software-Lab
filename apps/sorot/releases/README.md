# Arsip versi Sorot

Setiap versi disimpan pada direktorinya sendiri. Folder versi yang telah dipublikasikan bersifat arsip: jangan menimpa binari versi lama untuk memperbaiki atau menggantinya.

## Struktur rilis

Setiap versi yang terdaftar di `index.json` wajib memiliki:

- `release.json`: status/channel serta daftar artefak dengan nama file, format, arsitektur, dan SHA-256;
- `SHA256SUMS`: tepat satu baris untuk setiap artefak manifest, tanpa file hilang atau entri tambahan;
- file artefak yang sungguh ada;
- laporan pengujian yang menjelaskan lingkungan dan keterbatasannya.

Format berbeda antarversi. Jangan menambahkan .deb, .rpm, AppImage, wheel, ZIP, atau paket Arch hanya karena berkas itu bisa dibuat; catat hanya format yang memang diputuskan untuk dibagikan. Status `testing` berarti beta/testing, bukan stabil.

## Cara menambahkan versi

1. Buat folder baru, misalnya `releases/0.8.0/`; jangan mengubah artefak versi lama.
2. Buat `release.json` dan `SHA256SUMS` menggunakan hash aktual file final. Manifest dan checksum harus cocok dengan berkas byte-for-byte.
3. Tambahkan versi dan format yang tepat ke `index.json` (urutan lama ke baru).
4. Jalankan `python apps/sorot/validate_releases.py` dan tes integrasi website. Perbaiki semua kegagalan, termasuk tautan dokumentasi yang rusak.
5. Buka PR. Workflow GitHub memvalidasi rilis, lalu menyinkronkan `public/data/distribution-index.json` secara otomatis setelah merge. Tidak perlu meminta integrasi manual dan tidak perlu mengedit daftar manifest Sorot kedua kali.

Indeks web adalah hasil turunan, bukan sumber data. Jangan menambahkan versi ke `public/data/distribution-index.json` secara manual.

## Target yang belum siap

Distro/format yang belum teruji dicatat di `planned_targets`, bukan sebagai unduhan yang tersedia. Saat ini Arch Linux tetap eksperimental: PKGBUILD untuk inspeksi berada di `apps/sorot/experimental/arch/<versi>/`; belum ada artefak `.pkg.tar.zst` tervalidasi. Jangan menyajikan PKGBUILD itu sebagai paket rilis.

## Memeriksa artefak

Dari root repositori:

~~~
python apps/sorot/validate_releases.py
python -m unittest discover -s tests -p 'test_sorot_distribution_integration.py' -v
~~~

Atau pada direktori versi tertentu:

~~~
cd apps/sorot/releases/0.7.0
sha256sum -c SHA256SUMS
~~~

Checksum mendeteksi mismatch terhadap metadata; checksum bukan tanda tangan kriptografis penerbit. Status dan klaim kompatibilitas harus mengikuti laporan tes nyata.
