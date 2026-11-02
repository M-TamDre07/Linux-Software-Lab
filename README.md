# LISO LAB — Linux Software Lab

**LISO LAB (Linux Software Lab)** adalah identitas publik dan nama singkat untuk katalog software independen oleh Muhammad Andreatama. Nama lengkap Linux Software Lab tetap dipertahankan sebagai nama proyek dan repositori agar tautan, riwayat, serta integrasi yang ada tidak berubah. Website menggunakan HTML, CSS, JavaScript, dan JSON sebagai sumber data utama. Supabase menyimpan mirror katalog baca-saja yang disinkronkan dari GitHub; Vercel melayani website statis dengan fallback ke JSON lokal agar tetap berfungsi saat backend bermasalah.

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
ⶻ�q�^