# Website Maintenance Standard

Dokumen ini menjadi acuan maintenance tampilan publik LISO LAB. Tujuannya menjaga halaman mudah dipahami, konsisten, aksesibel, dan tidak mengiklankan kemampuan yang belum dibuktikan.

## Source of truth

- `public/data/software.json` adalah sumber metadata katalog yang dikonsumsi website.
- `apps/sorot/releases/index.json` dan manifest per versi adalah sumber daftar rilis Sorot. Halaman Sorot mengambil daftar versi dan laporan pengujian dari indeks/manifest tersebut.
- `public/data/distribution-index.json` adalah indeks distribusi yang dipakai website dan launcher. Jangan menambahkan klaim distro hanya dari user-agent browser.
- PaketScope menggunakan manifest artefak per versi di `apps/paketscope/releases/`. Klaim kompatibilitas harus mengikuti manifest, bukti CI, dan laporan pengujian; jangan menyamakan build container dengan uji desktop nyata.
- GitHub adalah sumber kebenaran; Supabase merupakan mirror katalog baca-saja. Pencarian publik tetap berjalan di browser.

## Kontrak navigasi dan layout

- Semua halaman publik utama memakai satu navigasi: Beranda, Jelajahi software, Launcher, Pendekatan, Instalasi, dan Kontribusi.
- Semua halaman publik utama memakai footer bersama yang mengarah ke katalog, launcher, source, pelaporan masalah, dan dukungan proyek.
- Setiap halaman harus memiliki satu `h1`, `main#main`, skip-link, canonical URL unik, dan tombol tema/menu dengan nama aksesibel.
- Gunakan `site.css` untuk fondasi, token awal, dan elemen global; gunakan `experience.css` untuk sistem pengalaman bersama; stylesheet khusus halaman hanya untuk kebutuhan yang benar-benar khusus.
- Pertahankan bahasa visual editorial yang sudah ada: tipografi Inter/Manrope, warna berbasis token, permukaan bersih, garis pemisah halus, dan tombol yang konsisten. Jangan menambah warna hard-coded atau efek dekoratif yang mengganggu hierarki informasi.

## Responsif dan aksesibilitas

- Gunakan grid/flex dengan `minmax(0, 1fr)` dan `min-width: 0` pada area yang berisi teks panjang atau kontrol.
- Prioritaskan alur satu kolom pada lebar layar kecil; kontrol pencarian/filter harus tetap dapat disentuh, dibaca, dan tidak menimbulkan horizontal scrolling.
- Semua kontrol interaktif harus dapat dijangkau keyboard dan memiliki `:focus-visible` yang jelas.
- Hormati `prefers-reduced-motion`, gunakan heading semantik, label form yang terhubung, status dinamis dengan `aria-live`, dan teks alternatif yang sesuai.
- Jangan memakai gambar konsep sebagai screenshot produk. Cantumkan label konsep pada setiap ilustrasi yang bukan tangkapan layar aplikasi.

## Informasi produk dan rilis

- Status `planned`, `testing`, `released`, dan `archived` tidak boleh dipertukarkan. Tombol unduhan hanya tampil untuk artefak HTTPS yang dicatat pada manifest valid.
- Jelaskan cakupan uji secara spesifik: versi, OS/container/desktop, arsitektur, backend grafis, serta pemeriksaan yang belum dilakukan.
- Jangan menyebut paket `.deb` sebagai bukti dukungan semua Debian/Ubuntu; minimum OS pada manifest harus dihormati.
- Jangan menyebut Xvfb atau Weston headless sebagai pengujian pada desktop fisik GNOME/KDE.
- Versi yang ditampilkan di beranda dan README harus sama dengan versi terbaru di indeks rilis. Pembaruan versi harus menyertakan laporan pengujian baru.
- Tautan anchor internal harus menunjuk ke ID yang benar-benar ada. Hindari tautan PR lama sebagai CTA permanen; gunakan source/docs yang stabil.

## Alur pencarian dan kompatibilitas

- Pencarian katalog berjalan lokal dan tidak mengirim kata kunci ke API.
- Jika mirror Supabase gagal, gunakan JSON statis yang lolos validasi.
- Jika indeks/manifest kompatibilitas tidak dapat diverifikasi, sembunyikan klaim paket dan nonaktifkan filter target sampai metadata valid kembali.
- Kegagalan metadata tidak boleh menghapus snapshot katalog terakhir yang valid atau menghambat pencarian nama/fitur.

## Checklist sebelum merge

1. Jalankan `python scripts/validate_catalog.py`, `python scripts/check_site_links.py`, `python scripts/check_docs_links.py`, dan `python scripts/validate_app_manifest.py`.
2. Jalankan `node --check` pada JavaScript publik yang berubah.
3. Jalankan `python -m unittest discover -s tests -v`.
4. Periksa konsistensi versi beranda, halaman detail, README, indeks rilis, dan manifest.
5. Uji lebar 360 px, 390 px, 768 px, dan desktop; periksa menu, tema, pencarian, filter, ekspor, footer, dan fokus keyboard.
6. Periksa deployment preview sebelum merge; verifikasi HTTP 200, JSON katalog, indeks distribusi, dan asset utama pada deployment production setelah merge.
