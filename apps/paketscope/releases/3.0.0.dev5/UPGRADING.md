# Memasang dan memperbarui PaketScope 3.0.0.dev5

Pratinjau pengembangan. Hanya Debian 13 yang didukung secara terbatas. Arch dan Fedora tidak didukung.

## Debian 13

Lihat `repo/INSTALL-UPDATE.md` untuk menambahkan repositori bertanda tangan, lalu:

    sudo apt update
    sudo apt install paketscope      # pasang pertama kali
    sudo apt upgrade paketscope      # perbarui di tempat, aplikasi lama tidak dihapus

Setelah pembaruan, tutup dan buka lagi PaketScope agar kode baru dimuat.

Pasang dari file tanpa repositori (hanya untuk uji):

    sudo apt install ./paketscope_3.0.0~dev5-1_all.deb

Verifikasi checksum dulu:

    sha256sum -c SHA256SUMS

## Arch Linux dan Fedora (eksperimental, tidak didukung)

- Arch: `makepkg -si` dari `arch/PKGBUILD` dengan `arch/paketscope-3.0.0.dev5.tar.gz` di folder yang sama. Belum dibangun dengan `makepkg`.
- Fedora: `rpmbuild -bb fedora/paketscope.spec` dengan `fedora/paketscope-3.0.0~dev5.tar.gz` di `SOURCES`. Belum dibangun di Fedora.

Kedua paket ini tidak menyediakan operasi paket yang berfungsi di distro tersebut.

## Membangun ulang dari sumber

    pip install .                    # memakai wheel atau pyproject yang sama
    dpkg-buildpackage -us -uc -b     # dari folder sumber untuk .deb
