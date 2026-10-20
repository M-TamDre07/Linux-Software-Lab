# Linux Software Lab

Katalog software desktop independen oleh Muhammad Andreatama, berfokus pada kebutuhan nyata pengguna Debian dan keluarga Linux. Website menggunakan HTML, CSS, dan JavaScript statis agar mudah dihosting, cepat dimuat, dan tidak membutuhkan database untuk katalog awal.

## Peta direktori

| Path | Fungsi |
|---|---|
| `index.html` | Landing page dan cuplikan katalog |
| `software/index.html` | Direktori software khusus dengan pencarian dan filter |
| `software/<slug>.html` | Halaman detail per software |
| `data/software.json` | Satu sumber data untuk metadata katalog |
| `data/software.schema.json` | Kontrak skema metadata versi 2 |
| `assets/css/site.css` | Sistem desain, tema, layout responsif, dan aksesibilitas |
| `assets/js/site.js` | Pencarian lokal, filter, pengurutan, URL state, dan pagination |
| `assets/images/` | Ikon dan artwork asli |
| `apps/<slug>/` | Source code aplikasi desktop/CLI/web |
| `scripts/` | Validator katalog dan pemeriksaan link statis |
| `tests/` | Tes untuk pemeriksaan metadata |
| `docs/` | Dokumentasi arsitektur, kontribusi, dan deployment |

## Jalankan secara lokal

Website tidak memerlukan build tool:

~~~bash
python3 -m http.server 8000
~~~

Buka `http://localhost:8000` untuk landing page dan `http://localhost:8000/software/` untuk direktori pencarian.

## Pemeriksaan sebelum perubahan di-merge

~~~bash
python3 scripts/validate_catalog.py
python3 scripts/check_site_links.py
node --check assets/js/site.js
python -m json.tool data/software.json > /dev/null
python -m json.tool data/software.schema.json > /dev/null
python3 -m unittest discover -s tests -v
~~~

GitHub Actions menjalankan pemeriksaan ini pada perubahan website. Ada workflow terpisah untuk tes source aplikasi PaketScope.

## Menambahkan software baru

1. Buat slug lowercase dengan tanda hubung, misalnya `sample-tool`.
2. Tempatkan source di `apps/sample-tool/` jika source dikelola dalam repo.
3. Buat halaman detail di `software/sample-tool.html`.
4. Letakkan ikon dan preview asli di `assets/images/`.
5. Tambahkan metadata secara lengkap ke `data/software.json`. Jangan menambah data software langsung di JavaScript.
6. Jalankan validator, tes, dan pemeriksaan link sebelum membuka pull request.

Panduan lengkap ada di `docs/ADDING_SOFTWARE.md`.

## Pencarian dan skalabilitas

Pencarian katalog berjalan di browser dan mencakup nama, deskripsi, kategori, versi, tag, keywords, fitur, dan platform. Kategori/platform dihasilkan dari metadata, status dapat difilter, hasil dapat diurutkan, dan halaman menampilkan 12 kartu per tahap. Kata kunci pencarian tidak dikirim ke layanan eksternal. Pola ini sengaja dipilih sebelum katalog memerlukan search backend.

## Vercel: penting membedakan website dan aplikasi

Website dipasang dari **root repository** `M-TamDre07/Portofolio`. Folder `apps/paketscope/` adalah aplikasi desktop Python/Qt, bukan website Vercel. Jangan membuat proyek Vercel terpisah dengan root directory `apps/paketscope`.

Gunakan proyek Vercel yang sudah melayani domain website, pastikan repository GitHub terhubung, root directory berada di root repo, dan build command tetap kosong/static sesuai konfigurasi yang sudah bekerja. Lihat `docs/VERCEL_DEPLOYMENT.md`.

## Prinsip

- Masalah pengguna lebih penting daripada jumlah fitur.
- Jangan klaim kompatibilitas tanpa pengujian.
- Status `planned`, `testing`, `released`, dan `archived` harus mencerminkan keadaan sebenarnya.
- Link unduhan hanya dipasang bila rilis benar-benar tersedia dan diverifikasi.
- Artwork konsep tidak boleh diberi label sebagai screenshot rilis.
- Tidak ada telemetry tersembunyi atau pengiriman kata kunci pencarian.
- Pertahankan aksesibilitas, tampilan responsif, reduced motion, dan navigasi keyboard.

## Kredit dan dukungan

Situs ini dirancang dan dikembangkan oleh Muhammad Andreatama. Dukungan sukarela tersedia melalui https://saweria.co/tamaandrea.

## PaketScope

PaketScope adalah aplikasi desktop terpisah dari website. Source dan perintah menjalankannya ada di `apps/paketscope/README.md`. PaketScope 2 saat ini masih development preview; tidak ada binary installer rilis atau audit keamanan independen.
