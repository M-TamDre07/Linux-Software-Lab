# Distribusi: Debian, Fedora, Arch, Flatpak, pembaruan

Status jujur tiap jalur. "Dibangun" berarti artefaknya dihasilkan dan diperiksa di lingkungan pembangunan (Ubuntu 24.04); "dipasang" berarti diuji di distro sasaran, dan itu **belum** terjadi untuk Fedora, Arch, dan Flatpak.

| Jalur | Perintah | Dibangun | Dipasang di distro sasaran |
|---|---|---|---|
| Debian 13 (`.deb`) | `make deb` | ya; lintian bersih; dibangun ulang identik | belum (Debian 13 bersih lewat `apt`) |
| Repositori apt bertanda tangan | `make apt-repo KEY=… URL=…` | ya; diuji dengan apt sungguhan | belum dari hosting nyata |
| Fedora 40+ (`.rpm`) | `make rpm` | ya (noarch, identik di dua build; percobaan dengan `RPM_NODEPS=1` karena host Ubuntu) | belum; `rpmlint` tidak dapat dijalankan di lingkungan ini |
| Arch (`PKGBUILD`) | `make dist` → `dist/arch/` | `PKGBUILD` dan `.SRCINFO` dihasilkan | belum (`makepkg`/`namcap` tidak ada) |
| Flatpak | `make flatpak [BASE=url]` | manifes dihasilkan dan terbaca `flatpak-builder` | belum dibangun (Flathub tidak terjangkau) |
| Wheel (pip/pipx) | `make dist` | ya | ya (venv Python 3.12) |

## Pembaruan tanpa menghapus
* Paket baru dipasang di atas yang lama di semua format; data dicadangkan otomatis saat peluncuran pertama.
* Repositori apt, Flatpak, dan (nanti) COPR/AUR membuat pembaruan muncul di Discover/pengelola paket.
* **Periksa pembaruan** (menu Bantuan) hanya aktif saat diklik. Ia membaca `latest.json` (satu GET HTTPS, tanpa pengenal) dan menunjukkan versi, catatan, dan tautan. Sorot tidak mengunduh atau memasang apa pun sendiri: mengganti program lewat jaringan tanpa tanda tangan yang diperiksa adalah risiko keamanan. Buat berkasnya dengan `make update-manifest BASE=https://alamat/berkas-rilis` dan simpan sebagai `apps/sorot/latest.json` di repositori.

## Fedora
`make rpm` menghasilkan `dist/rpm/sorot.spec` dan RPM noarch. Dependensi: `python3-pyside6` (Fedora 40+). Di Fedora sungguhan jalankan tanpa `RPM_NODEPS`, lalu uji `sudo dnf install ./sorot-*.rpm`, `rpm -V sorot`, dan `rpmlint`. Untuk distribusi: COPR (`copr-cli build`) memudahkan `dnf copr enable`; paket resmi Fedora membutuhkan proses review dan makro `%pyproject_*`.

## Flatpak
* ID aplikasi bawaan `io.github.M_TamDre07.Sorot` (dari akun GitHub). **Konfirmasikan** ke peninjau Flathub; ubah dengan `SOROT_FLATPAK_ID`.
* Dasar: `org.kde.Platform` 6.8 + `io.qt.PySide.BaseApp` 6.8 (menyediakan PySide6). Percobaan lokal: `make flatpak` lalu `scripts/build-flatpak.sh --build`.
* Izin: X11 dan Wayland, GPU, jaringan (hanya untuk fitur AI opsional), keyring (`org.freedesktop.secrets`). **Tanpa akses berkas rumah**: dialog Buka/Simpan memakai portal. rclone tidak ada di sandbox, jadi **integrasi Google Drive tidak tersedia** di Flatpak.
* Flathub mewajibkan URL sumber berhash (`make flatpak BASE=https://…`), AppStream valid, tangkapan layar yang dihosting, dan peninjauan manusia. Pengiriman ke Flathub dilakukan pengelola; skrip ini tidak mengirim apa pun.

## Yang masih dibutuhkan dari pengelola
Kunci GPG sendiri, tempat hosting (repositori apt, `latest.json`, berkas rilis), akun Flathub/COPR/AUR, dan persetujuan eksplisit untuk menerbitkan. Lihat [VERIFY.md](VERIFY.md).
