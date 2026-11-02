# Website Maintenance Standard

Dokumen ini menjadi acuan maintenance tampilan publik LISO LAB. Tujuannya menjaga halaman mudah dipahami, konsisten, aksesibel, dan tidak mengiklankan kemampuan yang belum dibuktikan.

## Source of truth

- public/data/software.json adalah sumber metadata katalog yang dikonsumsi website.
- apps/sorot/releases/index.json dan manifest per versi adalah sumber daftar rilis Sorot. Halaman Sorot mengambil daftar versi dan laporan pengujian dari indeks/manifest tersebut.
- public/data/distribution-index.json adalah indeks distribusi yang dipakai website dan launcher. Jangan menambahkan klaim distro hanya dari user-agent browser.
- PaketScope menggunakan manifest artefak per versi di apps/paketscope/releases/. Klaim kompatibilitas harus mengikuti manifest, bukti CI, dan laporan pengujian; jangan menyamakan build container dengan uji desktop nyata.
- GitHub adalah sumber kebenaran; Supabase merupakan mirror katalog baca-saja. Pencarian publik tetap berjalan di browser.

## Kontrak navigasi dan layout

- Semua halaman publik utama memakai satu navigasi: Beranda, Jelajahi software, Launcher, Pendekatan, Instalasi, dan Kontribusi.
- Semua halaman publik utama memakai footer bersama yang mengarah ke katalog, launcher, source, pelaporan masalah, dan dukungan proyek.
- Setiap halaman harus memiliki satu h1, main#main, skip-link, canonical URL unik, dan tombol tema/menu dengan nama aksesibel.
- Gunakan site.css untuk fondasi, token awal, dan elemen global; gun¶»§q«^