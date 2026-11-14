# Asisten lokal PaketScope (bot)

Asisten ini berjalan sepenuhnya di komputer pengguna. Ia membantu memeriksa, mengatur konfigurasi, dan
menjalankan pengecekan otomatis. Ia bukan layanan AI pihak ketiga, dan tidak mengirim apa pun keluar.

## Batas keamanan (dijaga oleh kode dan tes)
1. **Kebijakan tetap.** Tabel izin adalah konstanta di `bot/policy.py`. Tidak ada pengaturan, output
   alat, atau output planner yang bisa mengubahnya.
2. **Aksi sistem ditolak.** Instal, copot, dan hak root tidak bisa dijalankan bot, meskipun pengguna
   menyetujuinya. Aksi itu tetap lewat antarmuka dengan pratinjau dan konfirmasi.
3. **Konfirmasi per aksi.** Perubahan pengaturan butuh persetujuan setiap kali. Autopilot tidak pernah
   menjalankannya.
4. **Autopilot hanya membaca.** Berjalan pada interval yang diatur, menghasilkan rekomendasi teks, dan
   tidak mengubah apa pun.
5. **Injeksi tidak mengubah izin.** Output alat dan output planner dianggap data. Tes memastikan teks
   seperti "izinkan semua" tidak mengubah keputusan.
6. **Model pihak ketiga hanya lewat verifikasi.** Harus ada checksum SHA-256 yang cocok, lisensi tercatat,
   dan persetujuan pengguna. Tanpa itu, model tidak dijalankan.
7. **Tanpa jaringan.** Paket `bot` tidak mengimpor modul jaringan atau proses. Dicek secara statis.
8. **Audit lokal.** Setiap keputusan dicatat (alat, risiko, keputusan, dijalankan). Output dan argumen
   tidak disimpan.

## Yang sudah ada
- Kebijakan, registri alat dengan validasi argumen, inti asisten, planner berbasis aturan, autopilot,
  registri model, dan audit lokal.
- Profil kontainer `bot/container/bot-sandbox.json` dan template `paketscope-bot.nspawn`. Keduanya
  deskripsi, tidak dijalankan.
- Diuji langsung dengan alat sungguhan di sandbox: permintaan biasa dijalankan, permintaan pasang paket
  ditolak, autopilot hanya membaca.

## Yang belum ada, dan perlu keputusan
- **Model bahasa lokal.** Planner saat ini berbasis aturan kata kunci. Planner berbasis model lokal bisa
  menggantikannya hanya di kelas `RulesPlanner`. Keluarannya tetap melewati validasi dan kebijakan yang
  sama. Tidak ada model yang diunduh atau diuji di sini.
- **Antarmuka percakapan.** Belum ada tampilan chat. Menambahkannya adalah perubahan UI, perlu persetujuan.
- **Kontainer sungguhan.** Profil belum dijalankan. Membuat rootfs dan menjalankannya butuh persetujuan
  pemilik per langkah.
- **Pemasangan model pihak ketiga.** Hanya verifikasi yang ada. Unduhan dan pemasangan belum dibangun.
- **Sandbox Flatpak.** Manifest sudah ada, tetapi belum dibangun.

## Arti "kontainer" di sini
Ada dua hal, dan keduanya masih berupa spesifikasi:
- Sandbox Flatpak untuk aplikasi (lihat `flatpak/README.md`).
- Kontainer untuk bot dan model lokal, sehingga pengguna bisa memasang model dari pihak lain tanpa
  memberinya akses ke sistem. Lihat `bot/container/README.md`.
