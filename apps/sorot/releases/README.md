# Arsip versi Sorot

Setiap versi Sorot disimpan pada direktori terpisah. Direktori versi bersifat arsip: **jangan menimpa artefak versi lama** ketika merilis versi baru.

## Struktur

~~~text
releases/
├── README.md
├── 0.5.0/
│   ├── release.json
│   ├── RELEASE-NOTES.md
│   ├── RELEASE_READINESS.md
│   ├── TEST-REPORT.md
│   ├── SHA256SUMS
│   ├── sorot_0.5.0_all.deb
│   ├── sorot-0.5.0.tar.gz
│   └── sorot-0.5.0.zip
├── 0.5.8/  # contoh struktur versi mendatang; jangan dibuat hingga ada artefak nyata
└── 0.5.9/  # contoh struktur versi mendatang; jangan dibuat hingga ada artefak nyata
~~~

Setiap versi membawa semua format paket dan arsip sumber yang benar-benar tersedia untuk versi itu. Format dapat berbeda antarversi; misalnya .deb, .rpm, AppImage, tar.gz, dan ZIP hanya boleh dicantumkan bila artefaknya benar-benar sudah dibangun dan diuji sesuai klaimnya.

Setiap direktori versi harus berisi:
- release.json: versi, kanal/status, dan daftar artefak dengan SHA-256;
- SHA256SUMS: checksum atas setiap paket/arsip yang didistribusikan di direktori tersebut;
- catatan rilis dan laporan pengujian yang sesuai dengan versi itu;
- semua berkas paket serta source archive yang benar-benar tersedia.

## Memverifikasi artefak

Dari root repositori:

~~~bash
python apps/sorot/validate_releases.py
~~~

Atau validasi checksum untuk versi tertentu:

~~~bash
cd apps/sorot/releases/0.5.0
sha256sum -c SHA256SUMS
~~~

Jangan menyalin checksum versi lain, jangan mengganti paket di direktori lama dengan build baru, dan jangan menandai versi sebagai stabil hanya karena CI lulus. Status dan catatan harus sesuai dengan hasil pengujian aktual.

## Berpindah ke versi sebelumnya

Pilih artefak dari direktori versi yang ingin dipakai dan verifikasi checksum-nya terlebih dahulu. Untuk paket Debian, simpan salinan data penting dan gunakan paket versi yang dipilih. Jika APT menolak pemasangan versi yang lebih lama, penurunan versi dapat memerlukan opsi --allow-downgrades; jangan gunakan purge bila ingin mempertahankan konfigurasi pengguna. Arsip source tar.gz dan ZIP juga tetap tersedia per versi untuk audit atau build mandiri.

Versi yang tidak kompatibel atau bermasalah jangan dihapus dari arsip; tambahkan status/nota masalahnya dan pertahankan artefak serta checksum asli untuk reproduksibilitas.
