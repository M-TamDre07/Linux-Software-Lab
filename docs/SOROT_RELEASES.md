# Sorot — kebijakan dan riwayat rilis

Pembaruan: 24 November 2026

## Status terbaru

| Versi | Status | Kanal | Artefak yang dicatat | Rekomendasi |
| --- | --- | --- | --- | --- |
| 1.0.23 | `released` | `stable` | `.deb`, Python wheel | Rilis stabil dan versi utama yang direkomendasikan. QA maintainer dicatat pada [laporan pengujian 1.0.23](../apps/sorot/releases/1.0.23/TEST-REPORT.md). |
| 0.9.0 | `archived` | `development` | `.deb` | Tidak direkomendasikan untuk instalasi baru. Simpan hanya untuk kebutuhan lama/pengujian yang dipahami. |
| 0.8.0–0.5.0 | `testing` | `beta` | Mengikuti manifest tiap versi | Versi pengembangan lama; baca laporan pengujian dan jangan anggap sebagai stable. |

## Arti status dan kanal

- `released`: artefak terdaftar, tersedia untuk diunduh, dan memiliki manifest serta checksum. Ini adalah status publikasi.
- `testing`: build untuk pengujian yang belum dipromosikan menjadi rilis stabil.
- `archived`: versi lama yang disimpan untuk transparansi atau kompatibilitas, bukan pilihan untuk instalasi baru.
- `stable`: kanal rilis stabil yang telah melewati release gate dan disetujui maintainer.

Status publikasi dan kanal rilis adalah dua informasi terpisah. Sorot 1.0.23 berstatus `released` dan berada di kanal `stable`; status `released` sendiri tidak otomatis berarti stable.

## Unduh dan periksa

1. Pilih keluarga distribusi secara manual. Browser hanya dapat memberi petunjuk sistem operasi secara umum; user-agent tidak dapat memastikan nama distro Linux.
2. Pilih artefak yang formatnya sesuai. Paket `.deb` ditujukan untuk keluarga Debian/Ubuntu yang kompatibel; Python wheel memerlukan interpreter dan dependensi yang sesuai.
3. Versi lama, arsip, dan kanal non-stable menampilkan konfirmasi sebelum unduhan dilanjutkan.
4. Setelah mengunduh, cocokkan berkas dengan `SHA256SUMS` versi tersebut. SHA-256 membantu mendeteksi file yang berubah, tetapi bukan tanda tangan penerbit.
5. Unduhan tidak memasang aplikasi secara otomatis. Baca dependensi dan petunjuk pemasangan sebelum menjalankannya.

## Release gate sebelum stable

Rilis tidak boleh dipromosikan menjadi `stable` hanya karena berkas berhasil diunggah. Minimal:
- manifest, daftar artefak, dan checksum SHA-256 cocok dengan byte file yang dipublikasikan;
- pengujian unit/integrasi dan pemeriksaan packaging selesai;
- pengujian fungsional dan pemeriksaan kelayakan rilis disetujui maintainer;
- cakupan artefak, kebutuhan dependensi, dan batas kompatibilitas terdokumentasi;
- laporan QA mencatat keputusan rilis serta batas klaim dukungan;
- halaman katalog, Software Center, dokumentasi, dan mirror Supabase sinkron dengan sumber kanonis.

Status stable berlaku untuk versi dan format artefak yang dipublikasikan. Status ini bukan sertifikasi kompatibilitas universal untuk seluruh distro, desktop environment, arsitektur, atau konfigurasi Linux. Target tanpa paket nyata dan pengujian yang sesuai tetap dicatat sebagai `planned`.

## Sumber kanonis

- Riwayat versi: `apps/sorot/releases/index.json`
- Manifest per versi dan checksum: `apps/sorot/releases/<versi>/`
- Laporan QA 1.0.23: `apps/sorot/releases/1.0.23/TEST-REPORT.md`
- Validator: `apps/sorot/validate_releases.py`
- Sinkronisasi metadata web: `scripts/sync_distribution_index.py`
- Standar UI katalog: `docs/PRODUCT_UI_STANDARD.md`
