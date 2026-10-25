# Linux Software Lab

Katalog software independen oleh Muhammad Andreatama. Website menggunakan HTML, CSS, JavaScript, dan JSON sebagai sumber data utama. Supabase menyimpan mirror katalog baca-saja yang disinkronkan dari GitHub; Vercel melayani website statis dengan fallback ke JSON lokal agar tetap berfungsi saat backend bermasalah.

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
│   └── sorot/         # Sorot 0.5.0 Beta; paket dan dokumentasi beta
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

## Aset, SEO, dan integrasi sumber paket

- [Kredit aset dan kebijakan lisensi](docs/ASSET_CREDITS.md) mencatat aset visual asli dan aturan sebelum menambahkan aset pihak ketiga.
- [Integrasi katalog Supabase](docs/SUPABASE_INTEGRATION.md) menjelaskan mirror baca-saja, sinkronisasi CI, dan batas keamanan.
- [Rencana integrasi sumber paket](docs/PACKAGE_SOURCE_INTEGRATION.md) menetapkan identitas paket lintas distribusi, sumber resmi, pembaruan data, dan batas keamanan sebelum ingestion otomatis diaktifkan.
- Halaman publik menggunakan canonical URL, Open Graph/Twitter metadata, dan structured data yang sesuai. Pratinjau PaketScope tetap diberi label konsep; belum ada klaim rilis stabil.

## Prinsip

- Utamakan kebutuhan pengguna, bukan jumlah fitur.
- Cari secara lokal di browser; jangan mengirim kata kunci pencarian ke API eksternal.
- Jangan menambahkan analytics atau telemetry tersembunyi.
- Jangan mengklaim kompatibilitas sebelum diuji.
- Jangan menampilkan rilis atau tautan unduhan palsu.
- Simpan kredensial rahasia di luar public/; jangan commit token atau file .env.

## Sorot 0.5.0 Beta

Sorot adalah teleprompter desktop native untuk Linux. Ringkasan produk tersedia di [`apps/sorot/`](apps/sorot/README.md), sementara paket dan arsip sumber disimpan per versi di [`apps/sorot/releases/`](apps/sorot/releases/README.md), misalnya [`0.5.0 Beta`](apps/sorot/releases/0.5.0/RELEASE-NOTES.md). Setiap versi memiliki paket yang tersedia, arsip source, SHA256SUMS, manifest, serta catatan pengujian versi tersebut. Sorot masih beta; pengujian instalasi bersih Debian 13, compositor Wayland/X11 nyata, integrasi AI/cloud nyata, dan aksesibilitas pembaca layar masih perlu dilakukan. Arsip versi lama tidak ditimpa oleh versi baru.

## PaketScope 3 (pratinjau pengembangan)

Source aplikasi desktop native ada di `apps/paketscope/`. Versi source saat ini adalah `3.0.0.dev2` dan sudah terintegrasi di `main`. CI memvalidasi tes Python serta paket Debian di lingkungan Debian 13, tetapi ini tetap pratinjau pengembangan, bukan rilis stabil. Paket belum menjadi rilis publik bertanda tangan, belum melalui pengujian desktop menyeluruh, dan belum diaudit secara independen. Jangan menganggapnya siap untuk penggunaan produksi.

Arsitektur memisahkan UI di `paketscope/ui/`, layanan aplikasi di `services.py`, model dan parser di `domain.py`, serta adaptor OS untuk APT/dpkg dan Flatpak. Tindakan perubahan APT dibatasi pada satu paket dengan simulasi dan konfirmasi eksplisit; inventaris Flatpak masih read-only. Detail pengembangan dan batas keamanan ada di `apps/paketscope/docs/DEVELOPING.md`, `apps/paketscope/docs/PAKETSCOPE_V3_ARCHITECTURE.md`, dan `apps/paketscope/docs/SECURITY.md`.

### Menjalankan dari source

```bash
cd apps/paketscope
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
python -m pytest
python -m paketscope
```

Untuk menguji pemasangan atau penghapusan paket, gunakan mesin virtual Debian 13 dengan snapshot yang bisa dipulihkan. Jangan menguji transaksi paket pada sistem utama sampai pengujian desktop dan proses pemulihan selesai ditinjau.

## Kredit dan dukungan

Website dirancang dan dikembangkan oleh Muhammad Andreatama. Dukungan sukarela: https://saweria.co/tamaandrea


## Kontribusi dan atribusi

Pencipta awal dan maintainer proyek: **Muhammad Andreatama**. Sebelum mengerjakan perubahan untuk repositori resmi, hubungi maintainer dan tunggu persetujuan. Baca [CONTRIBUTING.md](CONTRIBUTING.md) untuk proses pengajuan, etika atribusi, dan batas kebijakan ini terhadap hak yang diberikan GPL-3.0.
