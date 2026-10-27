# Indeks versi Sorot

`index.json` adalah satu-satunya daftar versi Sorot yang dipelihara manual. Urutkan `versions` dari yang terlama ke terbaru. Masukkan versi hanya jika folder versi, manifest, checksum, dan artefak nyata tersedia.

Website dan helper terminal mengonsumsi indeks ini. GitHub Actions memvalidasi manifest/checksum lalu menyelaraskan `public/data/distribution-index.json` secara otomatis setelah perubahan indeks masuk ke `main`. Karena itu, **jangan mengubah daftar manifest Sorot secara manual di `public/data/distribution-index.json`**.

## Menambahkan versi baru

1. Buat folder versi baru; jangan menimpa folder versi yang lama.
2. Unggah hanya artefak yang memang siap dibagikan. Setiap artefak yang dicantumkan di manifest wajib tercantum dengan SHA-256 yang sama di `SHA256SUMS`.
3. Tambahkan `release.json` berisi versi, channel, status, artifacts, dan checksum yang tepat.
4. Tambahkan entri versi ke `index.json` dengan daftar format yang sama persis dengan manifest. Pertahankan versi lama di indeks agar arsip versi terdahulu tetap tersedia.
5. Jalankan `python apps/sorot/validate_releases.py` dan tes integrasi. Buka PR; workflow akan memeriksa rilis dan menyelaraskan indeks web setelah merge.
6. Target distro yang belum punya paket terbangun dan lolos pengujian masuk ke `planned_targets`, **bukan** ke `versions[].formats`.

`planned_targets` hanya informasi roadmap. Untuk menyatakan suatu distro tersedia, harus ada paket nyata dengan format, arsitektur dan checksum yang tervalidasi, lalu paket itu benar-benar diuji di distro yang diklaim. Status CI tidak menggantikan tes bersih pada distro nyata.
