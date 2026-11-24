# Sorot — kebijakan dan riwayat rilis

Pembaruan: 24 November 2026

## Status terbaru

| Versi | Status | Kanal | Artefak yang dicatat | Rekomendasi |
| --- | --- | --- | --- | --- |
| 1.0.23 | `released` | `beta` | `.deb`, Python wheel | Tersedia untuk diunduh; bukan stable. Laporan QA khusus dan uji instalasi bersih belum dipublikasikan. |
| 0.9.0 | `archived` | `development` | `.deb` | Tidak direkomendasikan untuk instalasi baru. Simpan hanya untuk kebutuhan lama/pengujian yang dipahami. |
| 0.8.0–0.5.0 | `testing` | `beta` | Mengikuti manifest tiap versi | Versi pengembangan lama; baca laporan pengujian dan jangan anggap sebagai stable. |

## Arti status dan kanal

- `released`: artefak terdaftar, tersedia, dan memiliki manifest serta checksum. Kata ini **tidak otomatis berarti stable**.
- `testing`: build Beta/pengujian yang belum dipromosikan.
- `archived`: versi lama yang disimpan untuk transparansi atau kompatibilitas, bukan pilihan untuk instalasi baru.
- `stable`: kanal stabil hanya boleh digunakan setelah release gate dan uji instalasi pada target yang dinyatakan selesai.

Status dan kanal adalah dua informasi terpisah. Contohnya, Sorot 1.0.23 berstatus `released` tetapi kanalnya `beta`.

## Unduh dan periksa

1. Pilih keluarga distribusi secara manual. Browser hanya dapat memberi petunjuk sistem operasi secara umum; user-agent tidak dapat memastikan nama distro Linux.
2. Pilih artefak yang formatnya sesuai. Paket `.deb` ditujukan untuk keluarga Debian/Ubuntu yang cocok; Python wheel memerlukan lingkungan Python dan dependensi yang sesuai.
3. Versi lama, arsip, dan kanal non-stable menampilkan konfirmasi sebelum unduhan dilanjutkan.
4. Setelah mengunduh, cocokkan berkas dengan `SHA256SUMS` versi tersebut. SHA-256 membantu mendeteksi file yang berubah, tetapi bukan tanda tangan penerbit.
5. Unduhan tidak memasang aplikasi secara otomatis. Baca dependensi dan petunjuk pemasangan sebelum menjalankannya.

## Release gate sebelum stable

Rilis tidak boleh dipromosikan menjadi `stable` hanya karena berkas berhasil diunggah. Minimal:
- manifest, daftar artefak, dan checksum SHA-256 cocok dengan byte file yang dipublikasikan;
- pengujian unit/integrasi dan pemeriksaan packaging selesai;
- instalasi bersih, peluncuran, dan penghapusan diuji pada setiap distro/versi OS yang diklaim didukung;
- dependensi, arsitektur, dan batas kompatibilitas terdokumentasi;
- laporan pengujian menyebutkan lingkungan, hasil, dan hal yang belum diuji;
- halaman katalog, Software Center, dokumentasi, dan mirror Supabase sinkron dengan sumber kanonis.

## Sumber kanonis

- Riwayat versi: `apps/sorot/releases/index.json`
- Manifest per versi dan checksum: `apps/sorot/releases/<versi>/`
- Validator: `apps/sorot/validate_releases.py`
- Sinkronisasi metadata web: `scripts/sync_distribution_index.py`
- Standar UI katalog: `docs/PRODUCT_UI_STANDARD.md`
