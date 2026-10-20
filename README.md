# Linux Software Lab

Katalog software desktop independen oleh Muhammad Andreatama untuk kebutuhan pengguna Debian dan keluarga Linux. Website memakai HTML, CSS, JavaScript, serta JSON statis tanpa framework build wajib.

## Struktur repository

~~~text
/
├── public/                    # Website dan aset yang dipublikasikan Vercel
│   ├── index.html
│   ├── assets/css/site.css
│   ├── assets/js/site.js
│   ├── assets/images/
│   ├── data/software.json
│   └── software/              # Halaman detail aplikasi
├── apps/paketscope/           # Source aplikasi desktop PaketScope 2
├── scripts/validate_catalog.py
├── docs/WEBSITE-ARCHITECTURE.md
├── .github/workflows/
└── vercel.json
~~~

## Menjalankan website secara lokal

~~~bash
python3 -m http.server 8000 --directory public
~~~

Buka http://localhost:8000.

## Menambah software ke katalog

1. Tambahkan record pada public/data/software.json mengikuti public/data/catalog.schema.json.
2. Buat halaman detail di public/software/<id>.html.
3. Simpan ikon dan preview di public/assets/images/.
4. Isi kata kunci dan fitur agar pencarian dapat menemukannya.
5. Jalankan validasi:

~~~bash
python scripts/validate_catalog.py
node --check public/assets/js/site.js
~~~

Setiap perubahan katalog akan diperiksa melalui GitHub Actions. Jangan menambahkan tautan rilis palsu atau menandai aplikasi sebagai released sebelum rilis benar-benar tersedia.

## Deployment Vercel

Vercel harus mengimpor repository GitHub M-TamDre07/Portofolio, bukan subfolder apps/paketscope. PaketScope merupakan aplikasi desktop Qt/Python dan tidak dijalankan sebagai website oleh Vercel.

Biarkan Root Directory kosong pada repository root. vercel.json menetapkan public sebagai output directory yang dipublikasikan. Ikuti docs/WEBSITE-ARCHITECTURE.md untuk langkah import dan troubleshooting.

## Prinsip

- Utamakan kebutuhan pengguna, bukan jumlah fitur.
- Jangan mengklaim kompatibilitas sebelum diuji.
- Jangan menyertakan telemetry tersembunyi atau mengirim inventaris pengguna.
- Gunakan data katalog terstruktur, tautan lokal yang tervalidasi, dan status rilis transparan.
- Jangan menyajikan concept art sebagai screenshot aplikasi rilis.

## PaketScope 2

Source aplikasi desktop berada di apps/paketscope/. Ini masih development preview; belum tersedia installer rilis bertanda tangan atau audit keamanan independen. Cara menjalankan, dependensi, batasan privasi, dan tes ada di apps/paketscope/README.md.

~~~bash
cd apps/paketscope
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m paketscope
python -m pytest
~~~

## Kredit dan dukungan

Website dirancang dan dikembangkan oleh Muhammad Andreatama. Dukungan sukarela tersedia melalui https://saweria.co/tamaandrea.
