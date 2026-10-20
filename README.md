# Linux Software Lab

Katalog software desktop independen oleh Muhammad Andreatama, berfokus pada kebutuhan nyata pengguna Debian dan keluarga Linux.

## Struktur
- \`index.html\` — katalog utama.
- \`assets/css/site.css\` — desain responsif, tema terang/gelap, komponen UI.
- \`assets/js/site.js\` — navigasi, tema, pencarian, filter, dan render katalog.
- \`data/software.json\` — metadata katalog software.
- \`software/\` — halaman detail proyek.

## Menjalankan secara lokal
Jalankan server HTTP dari root repository:

\`\`\`bash
python3 -m http.server 8000
\`\`\`

Buka http://localhost:8000.

## Menambah software
Edit \`data/software.json\` dan buat halaman detail di folder \`software/\`. Gunakan status \`testing\`, \`planned\`, atau \`released\`. Jangan menautkan repository atau unduhan sebelum tersedia dan diverifikasi.

## Prinsip
- Masalah pengguna lebih penting daripada jumlah fitur.
- Jangan menduplikasi fungsi bawaan Linux tanpa alasan yang jelas.
- Jangan klaim kompatibilitas tanpa pengujian.
- Rilis dan kode sumber ditautkan setelah benar-benar tersedia.
- Tidak ada telemetry tersembunyi atau pengiriman data pengguna dari katalog.

## Kredit dan dukungan
Situs ini dirancang dan dikembangkan oleh Muhammad Andreatama. Dukungan sukarela tersedia melalui https://saweria.co/tamaandrea.

Situs statis ini dapat dihosting di Vercel tanpa framework build tambahan. Pastikan domain yang benar telah dikonfigurasi di dashboard Vercel.
