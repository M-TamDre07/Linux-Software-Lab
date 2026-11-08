# Peta jalan: 0.8 → 0.9 → 1.0, dan apakah langsung ke 1.0.0

## Rekomendasi: bertahap
**Jangan langsung 1.0.0.** Versi 1.0.0 berarti "stabil dan didukung"; kriteria di bawah sebagian besar belum terbukti, dan beberapa hanya bisa dibuktikan oleh pemakaian nyata, bukan oleh pengujian otomatis.

| Rilis | Isi | Syarat selesai |
|---|---|---|
| **0.8.0** | Impor naskah (docx/odt/rtf/html/pdf, encoding), seret-lepas, Periksa pembaruan (opt-in), paket Fedora/Flatpak, identitas repo | Suite hijau semua platform uji; paket dibangun |
| **0.9.0** | Kontrol eksternal (CLI + soket lokal, pintasan lewat desktop, ponsel opsional); penanda gaya naskah. **Pembekuan fitur** | Fitur lengkap; semua jalur distribusi dipasang di distro sasaran oleh manusia |
| **0.9.x (RC)** | Hanya perbaikan bug dari pemakaian nyata | ≥ 2–4 minggu tanpa bug berat; CI hijau di GitHub |
| **1.0.0** | Pembekuan format data, ekstensi, profil, CLI | Semua kriteria di bawah terpenuhi |

## Kriteria 1.0 dan status saat ini (0.8.0)
| # | Kriteria | Status | Bukti / yang kurang |
|---|---|---|---|
| 1 | Suite otomatis hijau (Python 3.11/3.13, X11, Wayland) | ✅ | lihat TEST-REPORT |
| 2 | Tanpa crash terbuka; fuzz parser bersih | ✅ | fuzz 8.000 berkas dokumen, 60.000+ input konfigurasi |
| 3 | Pasang/upgrade/hapus bersih di Debian 13 | ❌ belum | hanya `dpkg --force-depends` di Ubuntu; upgrade 0.7.0→0.7.2 berjalan di KDE (laporan pengguna) |
| 4 | Fedora, Arch, Flatpak terpasang dan berjalan | ❌ belum | artefak ada; tidak ada mesin sasaran |
| 5 | CI GitHub hijau | ❌ belum | workflow belum pernah dijalankan |
| 6 | Desktop nyata: KDE ✔ sebagian, GNOME ✘; overlay selalu-di-atas, klik-tembus, transparansi dengan compositor | ⚠️ sebagian | KDE (Wayland+xcb) berjalan 0.7.2 per tangkapan layar; sisanya belum |
| 7 | Uji manual: beam-splitter, HiDPI, pembaca layar | ❌ belum | |
| 8 | Fitur inti lengkap (kontrol saat overlay di atas aplikasi lain) | ❌ 0.9 | |
| 9 | Format data, ekstensi, profil, CLI dibekukan dan didokumentasikan | ⚠️ skema 4 stabil sejak 0.7; belum dinyatakan beku | |
| 10 | Kanal pembaruan berjalan (repo apt/Flatpak/latest.json) dan kunci tanda tangan terbit | ❌ butuh persetujuan dan hosting | |
| 11 | Kebijakan keamanan aktif (pelaporan privat), lisensi konsisten (repo GPL-3.0 vs Sorot MIT) | ❌ tindakan pengelola | |
| 12 | Masa uji publik ≥ 2 minggu tanpa bug berat | ❌ | |

Tujuh dari dua belas belum terpenuhi dan tidak dapat dipenuhi oleh kode saja. Karena itu urutan yang realistis adalah 0.8.0 (ini), 0.9.0, beberapa RC, lalu 1.0.0.
