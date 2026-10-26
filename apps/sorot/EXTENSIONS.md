# Ekstensi Sorot

Sorot dapat diperluas tanpa mengubah kode intinya. Ada dua jenis ekstensi, dengan satu format manifest.

| Jenis | Isi | Dijalankan? | Persetujuan |
|---|---|---|---|
| **Deklaratif** | tema aplikasi, preset warna overlay, tugas AI, templat naskah | tidak ada kode | aktif otomatis, dapat dimatikan |
| **Kode** | berkas Python (`entry`) yang mendaftarkan transformasi, aksi, impor/ekspor, dan pendengar event | ya, di **proses terpisah** | **wajib** disetujui eksplisit |

> **Soal "mendukung semua ekstensi":** tidak ada standar ekstensi universal. Sorot mendukung ekstensi yang mengikuti **API ekstensi v1** di bawah ini. Ekstensi dari aplikasi lain tidak otomatis kompatibel.

## Memasang

* **Folder / ZIP:** halaman *Ekstensi* → *Pasang dari folder…* atau *Pasang dari ZIP…*. Pemasang menolak jalur berbahaya (zip-slip), tautan simbolik, arsip raksasa (>2000 berkas / 50 MB), dan manifest tidak valid.
* **Manual:** letakkan folder ekstensi di `~/.local/share/sorot/extensions/<id>/`, lalu *Muat ulang*.
* **Paket sistem:** `/usr/share/sorot/extensions/<id>/` (mis. dari paket `.deb` lain).
* **pip:** paket Python yang mendaftarkan entry point grup `sorot.extensions` ke sebuah paket yang berisi `sorot-extension.json`.

Pasang sebuah ekstensi dengan id yang sama dari folder pengguna akan mengganti salinan sistem/pip.

## Manifest `sorot-extension.json`

```json
{
  "id": "nama.ekstensi",          // wajib; huruf kecil, angka, . _ - (3-64)
  "name": "Nama tampil",          // wajib
  "version": "1.0.0",
  "api": 1,                       // wajib; harus 1
  "author": "Nama Kamu",
  "description": "Apa yang dilakukan.",
  "homepage": "https://contoh.id",   // opsional, harus https
  "license": "MIT",
  "min_app": "0.5.0",             // opsional
  "entry": "main.py",             // hanya untuk ekstensi kode
  "permissions": ["network", "filesystem", "subprocess", "clipboard"],  // informasi untuk pengguna
  "contributes": {
    "themes": [{"id": "senja", "name": "Senja", "base": "dark",
                "colors": {"bg": "#16101A", "accent": "#FF7A59"}}],
    "overlay_presets": [{"name": "Hangat", "text_color": "#FFD9B8", "background_color": "#1A0F14", "background_opacity": 78}],
    "ai_tasks": [{"id": "puisi", "label": "Jadikan puisi", "instruction": "Ubah menjadi puisi singkat."}],
    "templates": [{"name": "Salam", "text": "Halo!\n[jeda 2]\nSelamat datang."}]
  }
}
```

Kunci warna tema: `bg surface raised inset line line_strong text muted faint accent accent_ink live ok selection` (semua `#RRGGBB`). Entri yang tidak valid dibuang dan dilaporkan; manifest yang tidak valid membuat seluruh ekstensi tidak dipakai. Kunci tak dikenal diabaikan agar manifest dari versi lebih baru tetap terbaca.

Periksa ekstensimu: `sorot --validate-extension FOLDER` (statis) atau `... --run` (memuat dan mencetak perintah yang didaftarkan; ini menjalankan kodenya).

## API ekstensi kode (v1)

Berkas `entry` harus mendefinisikan `activate(api)` dan boleh mendefinisikan `deactivate()`.

```python
def activate(api):
    api.register_transform("besar", "Huruf besar", lambda teks: teks.upper())   # teks -> teks
    api.register_action("hitung", "Hitung kata", lambda teks: f"{len(teks.split())} kata")
    api.register_importer("md", "Markdown", [".md"], lambda path: open(path, encoding="utf-8").read())
    api.register_exporter("md", "Markdown", ".md", lambda teks, path: open(path, "w", encoding="utf-8").write(teks))
    api.on("playback.started", lambda data: api.log(f"mulai {data}"))
```

| Metode | Fungsi |
|---|---|
| `register_transform(id, label, fn)` | `fn(text) -> str`; diterapkan ke seleksi (atau seluruh naskah) dan **dapat di-undo** |
| `register_action(id, label, fn)` | `fn(text) -> None \| str \| {"notify": str, "set_text": str}` |
| `register_importer(id, label, [".ext"], fn)` | `fn(path) -> str` |
| `register_exporter(id, label, ".ext", fn)` | `fn(text, path)`; ekstensi yang menulis berkas |
| `on(event, fn)` | berlangganan event |
| `notify(msg)`, `log(msg)` | pesan status (maks. 50 per sesi) dan log |
| `data_dir` | folder tulis pribadi: `~/.local/share/sorot/extension-data/<id>/` |
| `app_version`, `api_version` | versi aplikasi dan API |

**Event** (pendengar hanya menerima yang dilanggannya; tidak ada yang membawa isi naskah): `app.started`, `app.closing`, `script.opened {name}`, `script.saved {name}`, `script.changed {words, characters}` (ditahan 1,5 detik), `overlay.shown`, `overlay.hidden`, `playback.started {total}`, `playback.paused {elapsed}`, `playback.finished {total}`, `playback.progress {elapsed, total}` (1 Hz).

Isi naskah hanya sampai ke ekstensi saat **kamu menjalankan** transformasi/aksi/ekspor miliknya.

Contoh ekstensi siap pakai belum disertakan dalam repositori ini. Gunakan struktur manifest dan API di atas sebagai kontrak, lalu tambahkan contoh hanya setelah berkasnya benar-benar tersedia dan diuji.

## Model keamanan (baca ini)

* Ekstensi kode berjalan **dengan izin akunmu**. Proses terpisah melindungi *stabilitas* (ekstensi yang macet, crash, atau salah tidak menjatuhkan Sorot), bukan *keamanan*. **Ini bukan sandbox.** Ekstensi tetap dapat membaca berkas, memakai jaringan, atau menjalankan program. Kolom `permissions` hanya informasi untuk pengguna dan tidak ditegakkan.
* Karena itu: tidak ada ekstensi kode yang berjalan sebelum kamu menyetujuinya di dialog yang menampilkan pembuat, izin yang dinyatakan, lokasi, dan sidik jari SHA-256 kodenya.
* Persetujuan terikat pada hash seluruh berkas ekstensi. **Perubahan satu byte pun mencabut persetujuan** sampai kamu menyetujui ulang.
* Lingkungan proses dibersihkan: variabel seperti `SOROT_API_KEY`, `OPENAI_API_KEY`, `AWS_*` **tidak** diteruskan. API key di keyring tidak pernah dibagikan lewat API.
* Setiap panggilan punya batas waktu (transform/aksi 30 dtk, impor/ekspor 60 dtk); proses yang tidak menjawab dibunuh. Tiga kegagalan beruntun menonaktifkan ekstensi sementara; panggilan berhasil mereset hitungan.
* Hasil transformasi dibuang jika naskah berubah saat ekstensi bekerja, dan hasil lebih dari 5 MB ditolak.
* Dapat dibatalkan kapan saja lewat menu *Ekstensi → Batalkan perintah yang berjalan*.
* Ekstensi deklaratif tidak mengeksekusi apa pun; tugas AI tambahan tetap hanya terkirim saat kamu menekan *Proses* dan menyetujui tujuannya.

Pasang ekstensi hanya dari sumber yang kamu percaya, seperti perangkat lunak lain.
