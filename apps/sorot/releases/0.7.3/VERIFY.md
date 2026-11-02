# Verifikasi unduhan, identitas pengelola, dan pembaruan

Dokumen ini untuk **pengguna** (cara memastikan berkas asli) dan **pengelola** (cara menerbitkannya dengan kredibel). Tidak ada perintah di sini yang dijalankan otomatis; menerbitkan rilis tetap keputusan pengelola.

## Untuk pengguna

1. **Periksa hash** setelah mengunduh: `sha256sum -c SHA256SUMS` (jalankan di folder berkas).
2. **Periksa tanda tangan** bila ada `SHA256SUMS.asc`:
   `gpg --import sorot-archive-keyring.asc && gpg --verify SHA256SUMS.asc SHA256SUMS`, lalu cocokkan **sidik jari** dengan yang diumumkan pengelola di kanal resminya (bukan hanya yang ada di unduhan yang sama).
3. **Lihat informasi paket** sebelum memasang: `dpkg-deb -I sorot_X_all.deb` (nama, pengelola, dependensi), `dpkg-deb -c sorot_X_all.deb` (isi), dan `appstreamcli` / Discover untuk deskripsi, lisensi (MIT) dan penulis setelah terpasang.
4. **Memperbarui**: pasang `.deb` baru di atas yang lama (`sudo apt install ./sorot_X_all.deb` atau buka di Discover). Versi lama diganti di tempat, tidak perlu menghapus; peluncuran pertama membuat cadangan otomatis. Aplikasi yang sedang terbuka tetap versi lama sampai ditutup dan dibuka lagi.

### Pembaruan otomatis lewat repositori (bila pengelola menyediakannya)

```bash
sudo install -d -m 0755 /etc/apt/keyrings
sudo curl -fsSL URL/sorot-archive-keyring.asc -o /etc/apt/keyrings/sorot-archive-keyring.asc
sudo curl -fsSL URL/sorot.sources -o /etc/apt/sources.list.d/sorot.sources
sudo apt update && sudo apt install sorot
```

Sesudah itu rilis baru muncul di Discover dan `apt upgrade`. apt menolak indeks yang dirusak atau ditandatangani kunci lain (diuji, lihat `tests/test_apt_repo.py`).

## Untuk pengelola

Kunci tanda tangan harus **milikmu** dan tetap di komputermu; skrip tidak membuat atau mengunggah kunci.

```bash
gpg --quick-gen-key "Muhammad Andreatama (rilis Sorot) <muhammadandreatama@outlook.com>" ed25519 sign 3y
gpg --list-secret-keys --keyid-format long          # catat sidik jari
make dist
make sign KEY=SIDIKJARI                              # dist/SHA256SUMS.asc
make apt-repo KEY=SIDIKJARI URL=https://alamat-hosting/apt   # dist/apt: pool/, dists/, kunci publik, sorot.sources, PASANG.txt
```

Unggah isi `dist/apt` ke hosting statis apa pun (mis. GitHub Pages) dan umumkan **sidik jari** di kanal resmi (README, profil, situs). Simpan cadangan kunci rahasia dan sertifikat pencabutan di tempat aman luring; bila kunci hilang atau bocor, semua pengguna harus mengganti kunci.

### Apa yang membuat paket tampak kredibel
* Nama, pengelola, dan kontak di `control`; pengembang, lisensi, deskripsi, dan riwayat rilis di `sorot.metainfo.xml` (AppStream) yang dibaca Discover.
* **Alamat situs/repositori publik** belum diisi: `Homepage` di `packaging/control.in`, `<url type="homepage">` dan `<url type="bugtracker">` di metainfo, serta `Source:` di `packaging/copyright` masih kosong sampai pengelola menentukan alamatnya. Ini yang paling menambah kepercayaan; isi sebelum rilis publik.
* Tangkapan layar di metainfo membutuhkan URL gambar yang dihosting; belum ada.
* ID komponen AppStream saat ini `sorot` (bukan domain terbalik) karena belum ada domain milik proyek; validator memberi peringatan, bukan galat.
* Tampilan "berkas lokal" di Discover (membuka `.deb` langsung) hanya menunjukkan data paket dasar dan nama berkas; info lengkap (ikon, penulis, lisensi) baru muncul setelah terpasang atau lewat repositori.
