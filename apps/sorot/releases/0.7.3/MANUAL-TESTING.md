# Pengujian manual Sorot 0.7.x

Dokumen ini adalah checklist untuk pengujian pada mesin desktop nyata. Catat distro, versi desktop/compositor, arsitektur, versi Python/PySide6, dan hasil setiap langkah. Jangan menandai lulus bila hanya diuji pada container atau compositor headless.

## Pra-pengujian
- [ ] Pastikan paket berasal dari artefak versi yang sedang diuji.
- [ ] Verifikasi SHA-256 menggunakan `sha256sum -c SHA256SUMS`.
- [ ] Catat lingkungan: distro/versi, arsitektur, GNOME/KDE/Xfce, Wayland/X11.

## Skenario inti
1. [ ] Pasang paket pada sistem uji yang bersih; pastikan dependensi dipenuhi tanpa `--force-depends`.
2. [ ] Jalankan Sorot dari menu aplikasi dan terminal; periksa versi, ikon, dan tidak ada traceback.
3. [ ] Buat, simpan, tutup, lalu buka kembali naskah; pastikan konten tetap utuh.
4. [ ] Uji overlay: transparansi, posisi, ukuran, selalu-di-atas, klik-tembus, mulai/jeda, dan kecepatan.
5. [ ] Uji mode cermin secara visual pada layar nyata; bandingkan arah teks dan kontrol.
6. [ ] Uji konfigurasi/profil valid dan nilai tidak valid; aplikasi harus tetap dapat dibuka dengan nilai aman.
7. [ ] Uji penutupan aplikasi melalui menu, SIGTERM, dan Ctrl+C; pastikan data tersimpan dan proses berhenti.
8. [ ] Uji ekstensi contoh, penghentian ekstensi, dan proses turunannya.
9. [ ] Uji upgrade dari versi sebelumnya dengan data pengguna yang sudah ada; pastikan cadangan dibuat dan naskah/profil/pengaturan tetap utuh.
10. [ ] Uji remove dan purge; catat apakah data pengguna dipertahankan/dihapus sesuai pilihan dan dokumentasi.

## Catatan hasil
- Tanggal dan penguji:
- Distro / versi / arsitektur:
- Desktop / compositor / session:
- Hasil tiap skenario:
- Log atau screenshot pendukung:
- Isu yang ditemukan:

**Batasan:** hasil pada Xvfb, Weston headless, atau container tidak membuktikan perilaku compositor GNOME/KDE pada desktop fisik. Debian 13 dan Arch harus diuji pada sistem bersih masing-masing sebelum klaim kompatibilitas.
