# Pengujian manual Sorot 0.8.0 Beta

Checklist ini ditujukan untuk mesin uji desktop nyata. Hasil pada container, Xvfb, atau Wayland headless tidak membuktikan perilaku GNOME/KDE pada perangkat pengguna. Jangan menandai item lulus sebelum pengujian dilakukan dan dicatat.

## Catatan lingkungan

- Tanggal dan penguji:
- Versi/format artefak:
- SHA-256:
- Distro dan versi:
- Arsitektur:
- Desktop/compositor:
- Sesi Wayland atau X11:
- Versi Python dan PySide6 (bila relevan):
- Hasil / tautan bukti:

## Persiapan

- [ ] Gunakan VM atau mesin uji dengan cadangan; jangan memakai sistem utama untuk percobaan awal.
- [ ] Verifikasi `SHA256SUMS` sebelum membuka atau memasang artefak.
- [ ] Catat metadata paket `.deb` dan dependensinya.
- [ ] Pastikan pengujian instalasi `.deb` dilakukan di Debian 13 bersih; jangan menggunakan `--force-depends` sebagai bukti kompatibilitas.

## Instalasi dan siklus aplikasi

1. [ ] Pasang paket pada sistem uji yang sesuai dan pastikan dependensi dipenuhi secara normal.
2. [ ] Jalankan Sorot dari menu aplikasi dan terminal; periksa versi, ikon, dialog, dan log tanpa traceback.
3. [ ] Buat, simpan, tutup, lalu buka kembali naskah; pastikan konten tetap utuh.
4. [ ] Uji keluar normal, SIGTERM, dan Ctrl+C; pastikan proses berhenti dan data yang semestinya tersimpan.
5. [ ] Uji upgrade dari versi sebelumnya dengan data pengguna yang sudah ada; pastikan cadangan dibuat dan naskah, profil, serta pengaturan tetap utuh.
6. [ ] Uji remove dan purge pada mesin uji; catat perbedaan perilaku dan dampak pada data pengguna.

## Fitur 0.8.0

7. [ ] Impor dokumen `.docx`, `.odt`, `.rtf`, `.html`, `.pdf`, dan `.txt` yang dibuat sendiri; periksa teks, encoding, jeda/baris, dan pesan kesalahan.
8. [ ] Seret-lepas setiap jenis dokumen yang didukung; berkas tidak didukung dan beberapa berkas sekaligus harus ditangani dengan aman.
9. [ ] Uji dokumen kosong, rusak, sangat besar, dan memiliki encoding berbeda; aplikasi harus menolak input tidak valid tanpa crash.
10. [ ] Uji **Bantuan → Periksa pembaruan** saat belum ada manifest; aplikasi harus menampilkan status yang jujur tanpa mengunduh atau memasang apa pun.
11. [ ] Pada lingkungan uji dengan endpoint manifest yang disediakan pengelola, uji respons valid, 404, redirect, HTTP non-TLS, checksum/format metadata yang salah, dan respons berukuran berlebihan.
12. [ ] Pastikan pemeriksaan pembaruan hanya berjalan setelah tindakan pengguna dan tidak mengirim cookie atau data naskah.
13. [ ] Uji mode cermin, overlay, transparansi, posisi, selalu-di-atas, klik-tembus, jeda, dan kecepatan pada sesi desktop nyata.
14. [ ] Uji ekstensi contoh dan proses turunannya; pastikan penghentian ekstensi tidak meninggalkan proses yatim.

## Kompatibilitas desktop

- [ ] GNOME Wayland dan GNOME X11/XWayland, bila tersedia.
- [ ] KDE Plasma Wayland dan X11, bila tersedia.
- [ ] HiDPI, skala 100–200%, font besar, keyboard-only, dan pembaca layar.
- [ ] Uji beam-splitter/layar eksternal bila fitur tersebut menjadi skenario penggunaan.

## Penutupan pengujian

- [ ] Simpan log, screenshot, versi paket, dan hasil tiap langkah.
- [ ] Catat setiap kegagalan secara terpisah; jangan menyamarkan kegagalan sebagai "belum dicoba".
- [ ] Perbarui `docs/COMPATIBILITY.md` hanya setelah hasil dapat direproduksi.
- [ ] Jangan mengubah status menjadi stable sebelum semua target yang diklaim benar-benar diuji.
