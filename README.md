# Linux Software Lab

Katalog software independen oleh Muhammad Andreatama. Website dibuat dengan HTML, CSS, JavaScript, dan JSON statis agar ringan, mudah dirawat, serta bisa menampung banyak aplikasi tanpa database pada tahap awal.

## Struktur repository

~~~text
/
├── public/                       # Satu-satunya direktori website yang diterbitkan Vercel
│   ├── index.html                # Halaman utama
│   ├── assets/
│   │   ├── css/site.css          # Komponen dasar dan layout lama yang tetap dipakai
│   │   ├── css/experience.css    # Sistem desain responsif bersama untuk pengalaman produk
│   │   ├── js/site.js            # Pencarian, filter, pengurutan, tema, dan navigasi
│   │   └── images/               # Ikon dan ilustrasi asli
│   ├── data/
│   │   ├── software.json         # Sumber data katalog
│   │   └── software.schema.json  # Kontrak metadata katalog versi 2
│   ├── software/
│   │   ├── index.html            # Direktori software lengkap
│   │   └── <slug>.html           # Halaman detail tiap aplikasi
│   ├── robots.txt
│   ├── sitemap.xml
│   └── google505d5a75f881baa2.html
├── apps/
│   ├── README.md                 # Pedoman folder per aplikasi
│   ├── paketscope/               # Source desktop native; bukan direktori website
│   └── prompter-overlay/         # Folder proyek kedua; masih tahap perencanaan
├── scripts/                      # Validator katalog dan pemeriksaan website
├── tests/                        # Tes regresi metadata, link, dan sitemap
├── docs/                         # Arsitektur, struktur software, rilis, deployment
├── .github/workflows/            # Pemeriksaan otomatis
└── vercel.json                   # Konfigurasi output dan header keamanan
~~~

## Menjalankan website secara lokal

~~~bash
python3 -m http.server 8000 --directory public
~~~

Buka http://localhost:8000 untuk halaman utama dan http://localhost:8000/software/ untuk direktori pencarian.

## Pemeriksaan sebelum merge

Jalankan perintah berikut dari root repository:

~~~bash
python scripts/validate_catalog.py
python scripts/check_site_links.py
node --check public/assets/js/site.js
python -m json.tool public/data/software.json > /dev/null
python -m json.tool public/data/software.schema.json > /dev/null
python -m json.tool vercel.json > /dev/null
python -m unittest discover -s tests -v
~~~

GitHub Actions mengulang pemeriksaan katalog, tautan HTML/aset, canonical URL, sitemap, sintaks JavaScript, JSON, dan tes regresi pada perubahan terkait website.

## Menambahkan software

1. Tambahkan metadata lengkap ke public/data/software.json.
2. Buat public/software/<slug>.html untuk halaman detail.
3. Simpan ikon dan ilustrasi di public/assets/images/.
4. Perbarui public/sitemap.xml dengan URL canonical halaman baru.
5. Jalankan seluruh pemeriksaan di atas sebelum membuka pull request.

Gunakan status planned, testing, released, atau archived secara jujur. Status released wajib memiliki releaseUrl HTTPS yang valid. Jangan menautkan unduhan yang belum tersedia atau menyajikan concept art sebagai screenshot aplikasi rilis. Lihat docs/ADDING_SOFTWARE.md dan docs/SOFTWARE_DIRECTORY_LAYOUT.md.

## Deployment Vercel

Hubungkan proyek Vercel ke repository GitHub M-TamDre07/Linux-Software-Lab dengan Root Directory tetap di root repository. vercel.json menetapkan public sebagai output website yang diterbitkan, sehingga source aplikasi, dokumentasi, tes, dan aset lama tidak ikut disajikan sebagai file situs.

PaketScope adalah aplikasi desktop Python/Qt di apps/paketscope/, bukan website terpisah untuk diimpor ke Vercel. Untuk proyek yang sudah terhubung, jangan membuat proyek duplikat hanya karena daftar Import menghilang atau gagal dimuat. Lihat docs/VERCEL_DEPLOYMENT.md.

## Prinsip

- Utamakan kebutuhan pengguna, bukan jumlah fitur.
- Cari secara lokal di browser; jangan mengirim kata kunci pencarian ke API eksternal.
- Jangan menambahkan analytics atau telemetry tersembunyi.
- Jangan mengklaim kompatibilitas sebelum diuji.
- Jangan menampilkan rilis atau tautan unduhan palsu.
- Simpan kredensial rahasia di luar public/; jangan commit token atau file .env.

## PaketScope (versi di cabang utama)

Setiap software memiliki folder tersendiri di apps/<slug>/. Lihat apps/README.md dan docs/SOFTWARE_DIRECTORY_LAYOUT.md. PaketScope 3 dikembangkan pada cabang feature/paketscope-v3-native; source v3 sudah memiliki README, LICENSE GPL-3.0, pyproject.toml, tests, dan dokumentasi arsitektur. Cabang tersebut belum digabung ke main dan belum menjadi rilis yang dapat dipasang. Lihat apps/paketscope/README.md pada cabang pengembangan untuk detailnya.

~~~bash
cd apps/paketscope
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m paketscope
python -m pytest
~~~

## Kredit dan dukungan

Website dirancang dan dikembangkan oleh Muhammad Andreatama. Dukungan sukarela: https://saweria.co/tamaandrea
