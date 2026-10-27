# Profil Tampilan

Profil Tampilan adalah satu berkas JSON yang menyimpan **seluruh tampilan teks** di overlay, sehingga mudah dipindah antar konteks (rekaman, presentasi, latihan) dan dibagikan ke orang lain.

## Memakai

*Tampilan → Profil tampilan*: pilih dari daftar untuk menerapkannya langsung. Tombol:

| Tombol | Fungsi |
|---|---|
| Simpan tampilan ini… | Menyimpan seluruh tampilan sekarang sebagai profil milikmu (`~/.local/share/sorot/profiles/`, izin `0600`). |
| Impor… | Membaca berkas profil, memvalidasinya, dan menambahkannya ke profilmu. **Tidak langsung dipakai**; pilih dari daftar. |
| Ekspor… | Menulis profil terpilih (atau tampilan sekarang) ke berkas JSON. |
| Hapus | Menghapus profil milikmu. Profil bawaan dan dari ekstensi tidak bisa dihapus. Pengaturan yang sedang dipakai tidak berubah. |

Bila pengaturanmu tidak sama dengan profil mana pun, daftar menampilkan *Kustom (belum disimpan)*.

Dari terminal: `sorot --profiles`, `sorot --export-profile "Rig cermin" rig.json` (atau `sekarang`), `sorot --import-profile rig.json`.

## Profil bawaan

Studio gelap (bawaan Sorot) · Kertas terang · Kontras tinggi · Bacaan lega · **Rig cermin** (teks dibalik, hitam pekat, rata tengah, hitung mundur 3 detik) · Presentasi ringan (kecil dan transparan).

## Pengaturan yang dikontrol

| Kunci | Nilai | Keterangan |
|---|---|---|
| `font_family` | teks | kosong = huruf bawaan; bila huruf tidak ada di komputer lain, Qt memakai penggantinya |
| `font_size` | 12–120 | |
| `font_weight` | `normal` `demibold` `bold` | |
| `line_spacing` | 100–250 | persen tinggi baris alami |
| `letter_spacing` | 0–30 | persen tambahan jarak huruf |
| `text_color` `background_color` | `#RRGGBB` | |
| `background_opacity` | 0–95 | |
| `text_align` | `left` `center` `right` `justify` | |
| `margin` | 0–120 | |
| `guide_enabled` `guide_position` `show_progress` | bool / 10–70 / bool | garis baca dan progres |
| `mirror` | bool | balik horizontal untuk beam-splitter |
| `start_delay` `show_countdown` | 0–120 detik / bool | jeda sebelum mulai dan hitung mundur besar |

Nilai di luar rentang dijepit, nilai tidak valid diganti nilai bawaan; aturannya sama dengan `config.json`.

## Format berkas

```json
{
  "sorot_profile": 1,
  "name": "Rig cermin",
  "description": "Teks dibalik untuk beam-splitter.",
  "values": { "font_size": 48, "font_weight": "bold", "mirror": true, "start_delay": 3 }
}
```

* `values` boleh **sebagian**: menerapkan profil hanya mengubah kunci yang tercantum.
* Hanya kunci di tabel di atas yang dibaca. Kunci lain (termasuk dari versi Sorot yang lebih baru) **diabaikan dan dilaporkan**.
* Profil **tidak pernah** mengubah posisi jendela, kecepatan gulir, pintasan, pengaturan AI/Drive, klik-tembus, atau apa pun di luar tampilan, jadi mengimpor profil orang lain tidak mengubah perilaku aplikasi.
* Batas: 64 KB per berkas, nama 1–60 karakter, maksimal 200 profil milikmu. Nama profil bawaan tidak bisa dipakai ulang.
* Berkas yang rusak atau tautan simbolik di folder profil dilewati dan tidak pernah menghentikan Sorot.

## Dari ekstensi

Ekstensi deklaratif dapat menyumbang `display_profiles`; lihat [EXTENSIONS.md](../../EXTENSIONS.md) dan `examples/extensions/contoh.tema-senja`. Profil ekstensi muncul sebagai `Nama · Ekstensi` dan hilang bila ekstensinya dimatikan.

## Mode cermin dan hitung mundur

* **Mode cermin** membalik teks overlay dan pratinjau secara visual untuk rig beam-splitter. Hanya tampilan: tombol overlay dan bingkai jendela tidak dibalik. Fitur ini memakai efek grafis Qt dan **belum diuji pada compositor nyata** (lihat [TEST-REPORT.md](TEST-REPORT.md)).
* **Hitung mundur** menampilkan angka besar di overlay selama “Jeda sebelum mulai” (di *Gulir*). Bila jeda 0 detik, tidak ada hitung mundur.

## Belum ada (rencana)

Warna berbeda per elemen (baris yang sedang dibaca, teks yang sudah lewat, isyarat), penanda gaya di dalam naskah (`# Judul`, `**tebal**`), dan templat naskah bergaya. Profil v1 sengaja dibatasi pada pengaturan yang sudah dapat dirender dengan aman.
