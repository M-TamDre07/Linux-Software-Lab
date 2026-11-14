# Verifikasi unduhan dan identitas rilis Sorot 0.8.0

Dokumen ini membedakan pemeriksaan integritas berkas dari verifikasi identitas penerbit. Status rilis 0.8.0 tetap **Beta/testing**; daftar tes otomatis tidak menggantikan uji instalasi pada distro sasaran.

## Untuk pengguna

1. Unduh `SHA256SUMS` dari direktori versi yang sama dengan artefak.
2. Jalankan pemeriksaan hash di direktori unduhan:

   ```bash
   sha256sum -c SHA256SUMS
   ```

   Hash yang cocok mendeteksi perubahan berkas terhadap checksum yang diterbitkan. Hash **bukan** tanda tangan digital dan tidak membuktikan siapa penerbitnya.
3. Periksa metadata paket sebelum instalasi:

   ```bash
   dpkg-deb -I sorot_0.8.0_all.deb
   dpkg-deb -c sorot_0.8.0_all.deb
   ```

4. Artefak `.tar.gz`, `.zip`, dan `.whl` adalah arsip sumber/distribusi Python, bukan paket installer desktop Debian.
5. Jangan menganggap file ini sebagai rilis stabil. Laporan 0.8.0 menyebut pengujian pada Ubuntu container; instalasi bersih Debian 13, Fedora, Arch, dan Flatpak belum disahkan.

## Tanda tangan penerbit

Direktori rilis 0.8.0 saat ini menyediakan `SHA256SUMS`, tetapi tidak menyediakan `SHA256SUMS.asc` atau keyring penerbit. Karena itu, verifikasi GPG belum tersedia untuk artefak ini. Jangan mengimpor kunci dari arsip yang sama dan menganggapnya sebagai identitas tepercaya.

Sebelum distribusi bertanda tangan diaktifkan, pengelola perlu membuat kunci GPG sendiri, menyimpan kunci privat secara luring, menerbitkan sidik jari melalui kanal independen, lalu menandatangani checksum. Jangan pernah menaruh kunci privat di repositori atau paket.

## Catatan pembaruan

Pemasangan paket baru di atas versi sebelumnya dapat mengganti file program; jangan hapus data pengguna secara manual. Uji skenario upgrade pada mesin virtual/sistem uji dengan cadangan terlebih dahulu. Fitur **Bantuan → Periksa pembaruan** bersifat opt-in dan tidak mengunduh atau memasang paket secara otomatis. `latest.json` belum boleh dianggap kanal distribusi aktif sebelum URL hosting dan checksum rilis diverifikasi oleh pengelola.
