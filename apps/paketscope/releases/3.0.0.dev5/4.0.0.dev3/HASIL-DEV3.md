# Hasil 4.0.0.dev3: asisten lokal, autopilot, registri model, kontainer

## Penjelasan tiga poin
- **"LLM".** Yang dimaksud adalah bot lokal: membantu memeriksa, mengatur konfigurasi, dan pengecekan
  otomatis. Tidak ada layanan AI pihak ketiga, dan tidak ada data yang dikirim keluar.
- **"Kontainer".** Dua hal: sandbox Flatpak untuk aplikasi, dan kontainer tempat bot serta model lokal
  berjalan. Di dalam kontainer itu pengguna bisa memasang model lokal dari pihak lain tanpa memberinya
  akses ke sistem.
- **Upload.** Anda yang mengunggah ke GitHub. Panduannya ada di `UNGGAH-KE-GITHUB.md`.

## Yang dibangun
| Bagian | Isi | Uji |
|---|---|---|
| Kebijakan | Tabel izin tetap. Aksi sistem ditolak untuk bot. Perubahan butuh konfirmasi. Autopilot hanya baca. | 9 tes |
| Registri alat | 9 alat dengan argumen divalidasi. Alat istimewa hanya terdaftar sebagai "ditolak". | 6 tes |
| Inti asisten | Planner dan output alat diperlakukan sebagai data. Injeksi tidak mengubah keputusan. Audit tanpa output. | 9 tes |
| Autopilot | Hanya alat baca yang ditandai, sesuai interval, menghasilkan rekomendasi teks. | 4 tes |
| Registri model | Harus ada checksum cocok, lisensi, dan persetujuan pengguna. | 6 tes |
| Isolasi | Paket bot tidak mengimpor modul jaringan atau proses. Profil kontainer diperiksa. | 4 tes |

Total: **375 tes lulus**, tiga kali berturut-turut. Validasi AppStream berhasil. Paket lolos lintian.
GUI berjalan dari layout paket tanpa error.

## Dicoba dengan alat sungguhan di sandbox
- Permintaan biasa (lingkungan, sumber APT, pembaruan): dijalankan, hasilnya nyata.
- Permintaan "pasang paket firefox": **ditolak**, tidak menyentuh apa pun.
- Autopilot: hanya menjalankan alat baca.
- Log audit: mencatat keputusan, tanpa output dan argumen.

## Yang belum ada, dan jujur
- **Model bahasa lokal belum ada.** Planner sekarang berbasis aturan kata kunci. Model lokal bisa
  menggantikan planner itu nanti, dan keluarannya tetap melewati kebijakan yang sama.
- **Tidak ada antarmuka chat.** Itu perubahan UI, perlu persetujuan Anda.
- **Kontainer belum dijalankan.** Profil hanya deskripsi. Membuat rootfs dan menjalankannya butuh
  persetujuan Anda per langkah.
- **Model pihak ketiga belum bisa diunduh.** Hanya verifikasi yang ada.
- **Sandbox Flatpak belum dibangun.** Manifest sudah ada.
- **Semua uji di Ubuntu sandbox**, bukan Debian 13.

## Yang perlu Anda putuskan
1. Apakah antarmuka chat boleh dibangun? Itu perubahan UI.
2. Model lokal mana yang akan dipakai, dan apakah Anda mau saya siapkan jalur pemasangannya lewat
   registri yang sudah diverifikasi?
3. Kontainer untuk bot: apakah Anda setuju kita membuat rootfs dan mengujinya di laptop, dengan
   persetujuan per langkah seperti sebelumnya?
