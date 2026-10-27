# Memperbarui Sorot

Ringkasnya: **program dan data dipisah.** Memasang versi baru tidak menyentuh naskah dan pengaturanmu (`~/.config/sorot`, `~/.local/share/sorot`). Sejak 0.6.0, saat pertama kali dijalankan setelah versi berubah, Sorot membuat **cadangan otomatis terverifikasi** sebelum menyimpan apa pun dalam format baru, sehingga kamu selalu bisa kembali.

> Saat ini rilis dibagikan sebagai berkas (`.deb`, `.whl`, arsip sumber, `PKGBUILD`). Berdasarkan materi proyek, belum ada repositori apt, paket AUR, atau rilis PyPI yang dipublikasikan, dan Sorot **tidak memeriksa pembaruan lewat internet** (sengaja: aplikasi tidak menghubungi siapa pun tanpa tindakanmu).

## Tiga langkah

```bash
sorot --upgrade-info      # 1. lihat versi, cara pemasangan, dan perintah pembaruan yang sesuai
sorot --backup            # 2. (opsional, disarankan) cadangan manual sebelum memperbarui
# 3. pasang versi baru dengan cara yang sama seperti memasang yang lama (tabel di bawah)
```

`sorot --upgrade-info` mengenali cara pemasanganmu dan mencetak perintah yang tepat.

## Memperbarui menurut cara pemasangan

| Cara pasang | Perintah pembaruan | Catatan |
|---|---|---|
| Debian/Ubuntu `.deb` | `sudo apt install ./sorot_0.7.0_all.deb` | Menggantikan versi lama di tempat. Paket `tama-prompter` (≤0.4.x) dihapus otomatis. |
| Arch Linux | **Belum didukung sebagai jalur rilis 0.7.0.** Tidak ada paket `.pkg.tar.zst` yang divalidasi. Jangan jalankan `makepkg -si` dari arsip rilis ini. | `PKGBUILD` masih eksperimen dan dipindahkan ke [`apps/sorot/experimental/arch/0.7.0/`](../../experimental/arch/0.7.0/). Lihat [panduan distribusi](../../DISTRIBUTION.md). |
| pipx | `pipx install --force ./sorot-0.7.0-py3-none-any.whl` | |
| pip (venv) | `python -m pip install --upgrade ./sorot-0.7.0-py3-none-any.whl` | |
| Skrip pengguna | `./scripts/install-user.sh` dari sumber versi baru | Aman diulang; hanya mengganti venv di `~/.local/share/sorot/venv`. |
| Salinan sumber | `git pull`, lalu `python -m pip install -e ".[dev]"` | |

Berganti cara pasang (mis. dari skrip pengguna ke paket) aman bagi datamu, tetapi hapus yang lama agar tidak ada dua salinan yang saling menimpa perintah `sorot` di `PATH`.

## Jalur versi

| Dari | Ke 0.7.0 | Yang terjadi |
|---|---|---|
| 0.6.x | langsung | Cadangan otomatis dibuat. Skema pengaturan naik 3 → 4: hanya **menambah** kunci tampilan baru (`font_weight`, `line_spacing`, `letter_spacing`, `mirror`, `show_countdown`, `profile`) yang nilai bawaannya persis sama dengan tampilan lama; tidak ada yang berubah untukmu. Profil milikmu (`~/.local/share/sorot/profiles/`) ikut dicadangkan. |
| 0.5.x | langsung | Data dipakai di tempat. Tidak ada perubahan skema (tetap versi 3). Cadangan otomatis dibuat pada peluncuran pertama (data ada tetapi belum ada catatan versi). |
| 0.4.x (*Tama Prompter*) | pasang 0.7.0 | Data diimpor sekali dari `~/.config/tama-prompter` dan `~/.local/share/tama-prompter`; **berkas lama tidak diubah**. API key keyring lama tetap terbaca. |
| 0.3.x | pasang 0.7.0 | Pengaturan dan naskah terakhir diimpor sekali dari `~/.config/TamaAndrea/TamaPrompter.conf` (hanya dibaca). Kamu dapat melompat langsung; tidak perlu singgah di 0.4/0.5. |
| < 0.3 | — | Tidak didukung. |

Hanya impor dari instalasi lama yang berjalan otomatis; **jangan menghapus folder lama** (`tama-prompter`, `TamaAndrea`) sampai kamu yakin semuanya terbawa.

## Apa yang terjadi saat peluncuran pertama setelah pembaruan

1. Sorot membandingkan versinya dengan catatan di `~/.local/state/sorot/version.json`.
2. Jika berbeda (naik **atau turun**), ia membuat `~/.local/share/sorot/backups/sorot-backup-auto-<versi>-<waktu>.zip` **sebelum** menyimpan apa pun. Lima cadangan otomatis terbaru disimpan; cadangan manual tidak pernah dihapus otomatis.
3. Pengaturan lama dimigrasikan di memori lewat rantai langkah berurutan (`MIGRATIONS` di `core/config.py`), baru ditulis ulang saat pertama menyimpan. Kunci yang tidak dikenal dipertahankan.
4. Jendela utama menampilkan satu pemberitahuan berisi nama cadangan. Gagal membuat cadangan **tidak** menghalangi aplikasi mulai (hanya dicatat di log dan diberitahukan).

Cadangan otomatis dilewati jika data lebih dari 200 MB (mis. data ekstensi sangat besar); gunakan `sorot --backup` secara manual.

## Isi cadangan

| Termasuk | Tidak termasuk |
|---|---|
| `config.json` (+ `.bak`, berkas karantina), draf, riwayat draf, pustaka naskah, **profil tampilan milikmu**, ekstensi terpasang dan datanya | **API key** (ada di keyring atau variabel lingkungan), log, kunci instance, folder cadangan itu sendiri, tautan simbolik |

Cadangan **tidak dienkripsi** dan berisi naskahmu. Simpan di tempat yang pantas, sama seperti naskah aslinya. Berkas cadangan dibuat dengan izin `0600`.

## Kembali ke kondisi sebelumnya (rollback)

```bash
sorot --upgrade-info                         # daftar cadangan
# tutup Sorot sepenuhnya, lalu:
sorot --restore ~/.local/share/sorot/backups/sorot-backup-auto-0.7.0-….zip
```

* Pemulihan memeriksa struktur, nama berkas, dan **SHA-256 setiap berkas** sebelum menulis apa pun; cadangan yang rusak atau diubah ditolak tanpa mengubah datamu.
* Pemulihan **menimpa** berkas dengan nama yang sama dan **tidak menghapus** berkas lain. Kondisimu sebelum memulihkan disimpan dulu sebagai `…-pre-restore-…zip`, jadi pemulihan pun bisa dibatalkan.
* Ditolak jika Sorot masih berjalan.

Untuk **menurunkan versi program**: pasang versi lama (perintah di tabel di atas dengan berkas lama), lalu pulihkan cadangan dari versi itu bila perlu. Versi yang lebih lama membaca berkas pengaturan yang lebih baru dengan mempertahankan kunci yang tak dikenalnya, tetapi tidak menjamin semua fitur baru berfungsi; Sorot memberi tahu bahwa ia diturunkan.

## Ekstensi saat memperbarui

* Persetujuan ekstensi kode terikat pada **hash kodenya**, bukan pada versi Sorot, sehingga bertahan setelah pembaruan. Mengubah satu byte ekstensi tetap mencabut persetujuan.
* API ekstensi v1 stabil selama seri 0.x ini; manifest dengan `"api": 1` tetap dibaca. Ekstensi dapat menyatakan `min_app`.
* Ekstensi pengguna ada di cadangan; ekstensi sistem (`/usr/share/sorot/extensions`) dikelola paketnya.

## Jika ada masalah

| Gejala | Langkah |
|---|---|
| Pengaturan kembali ke bawaan | Berkas rusak dikarantina sebagai `config.json.corrupt-*`; pilih Berkas → Pulihkan pengaturan, atau `sorot --restore` cadangan terbaru. |
| `sorot --restore` berkata Sorot sedang berjalan | Tutup jendela Sorot; jika tetap muncul, `pgrep -f sorot`. Kunci basi (proses sudah mati) diabaikan. |
| “hash tidak cocok” | Cadangan rusak atau diubah; pakai cadangan lain. Tidak ada yang ditulis. |
| Perintah `sorot` masih versi lama | Ada dua salinan di `PATH`; `which -a sorot` lalu hapus yang lama. |

## Untuk maintainer: merilis versi baru

```bash
python3 scripts/release.py bump 0.7.0 --date 2026-12-01   # ubah tempat-tempat mekanis + kerangka changelog
# isi entri CHANGELOG.md dan packaging/debian-changelog (kata TODO membuat `check` gagal)
make release-check test
make dist
```

Jika skema pengaturan naik: tambahkan langkah `N → N+1` ke `MIGRATIONS` di `core/config.py`; `tests/test_upgrade.py` gagal bila langkah itu tertinggal. Jangan mengubah `BACKUP_FORMAT` tanpa tetap membaca format lama.

Yang **belum** diuji: instalasi bersih Debian 13 melalui APT dengan dependensi nyata, pembaruan di mesin bersih, desktop/compositor nyata, dan seluruh jalur Arch (`makepkg`, `namcap`, instalasi/penghapusan Pacman). Lihat [TEST-REPORT.md](TEST-REPORT.md).
