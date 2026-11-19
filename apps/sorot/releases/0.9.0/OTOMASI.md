# Otomasi, LLM lokal, kontainer, dan Flatpak (0.9.0)

Halaman **Otomasi** (Ctrl+7) menyatukan empat hal. Semuanya **opsional** dan tidak aktif sendiri.

| Bagian | Fungsi | Bawaan |
|---|---|---|
| Server LLM lokal | mencari Ollama / LM Studio / llama.cpp di `127.0.0.1`, memilih model | tidak mencari sampai ditekan |
| Soket kontrol | `sorotctl` mengendalikan Sorot yang berjalan | **mati** |
| Resep otomasi | daftar langkah tetap, minta konfirmasi | 3 resep contoh |
| Pemeriksaan sistem | daftar periksa hanya-baca (`sorot --doctor`) | dijalankan manual |

**Sorot tidak pernah menjalankan, menghentikan, atau memasang kontainer maupun server LLM.** Anda yang menjalankannya; Sorot hanya melihat apakah ada yang menjawab di loopback.

## 1. LLM lokal

Ollama, LM Studio, dan `llama-server` (llama.cpp) berbicara format API yang sama dengan layanan AI yang sudah didukung Sorot, jadi "model lokal" hanyalah alamat di komputer ini.

* Port bawaan yang dicari: Ollama 11434, LM Studio 1234, llama.cpp 8080. Alamat lain bisa diisi manual di dialog Asisten AI.
* Pencarian hanya `GET /v1/models` ke loopback: tanpa isi naskah, tanpa kredensial, tanpa mengikuti pengalihan, tanpa proxy.
* **Server lokal tidak butuh API key.** Untuk alamat loopback Sorot tidak mengirim header `Authorization` sama sekali. Layanan jarak jauh tetap wajib berkunci dan tetap menampilkan peringatan sebelum naskah dikirim.
* Halaman Otomasi → **Pakai server dan model ini** mengisi alamat dan model layanan AI. Naskah tidak keluar dari komputer.

### Server dalam kontainer
Resep ada di `packaging/containers/` (terpasang ke `/usr/share/sorot/containers`; di Flatpak `/app/share/sorot/containers`). Detail dan aturan keamanannya ada di `README.md` di folder itu. Ringkas:

```bash
cd /usr/share/sorot/containers
docker compose -f ollama.compose.yaml up -d                 # atau: podman compose ...
docker compose -f ollama.compose.yaml exec ollama ollama pull NAMA_MODEL
```
Port diterbitkan hanya di `127.0.0.1`, tanpa hak istimewa, `restart: "no"`. Tambahan GPU: `ollama.gpu-nvidia.yaml` atau `ollama.gpu-amd.yaml`.

## 2. Soket kontrol dan `sorotctl`

Aktifkan di halaman Otomasi. Sorot lalu membuka soket Unix di `$XDG_RUNTIME_DIR/sorot/control.sock` (di Flatpak: `$XDG_RUNTIME_DIR/app/<ID>/control.sock`).

```bash
sorotctl status          # informasi (hanya baca)
sorotctl play | pause | toggle | reset | show | hide
sorotctl speed 2         # kecepatan +2 langkah (-10..10)
sorotctl recipes
sorotctl run "Mulai rekaman"   # Sorot meminta konfirmasi di jendelanya
```
Kode keluar: 0 berhasil, 1 ditolak Sorot, 2 salah pakai, 3 Sorot tidak terjangkau. `--json` mencetak balasan mentah.

**Jaminan keamanan (masing-masing ada tesnya di `tests/test_control.py`):**
* Mati secara bawaan; tidak ada TCP, hanya soket Unix.
* Folder 0700, soket 0600, dan setiap sambungan diperiksa `SO_PEERCRED`: hanya pengguna yang sama dilayani. Tanpa `XDG_RUNTIME_DIR` soket **tidak dibuka**; tidak pernah jatuh ke `/tmp`.
* Protokol: satu objek JSON per baris, maksimum 4 KB, batas waktu diam, batas sambungan dan jumlah permintaan.
* Daftar perintah tetap: `ping, version, status, show, hide, play, pause, toggle, reset, speed, recipes, run`. **Tidak ada** perintah untuk membaca berkas, mengganti naskah, menjalankan program, atau mengakses jaringan. Pesan galat internal tidak pernah dikirim ke klien.
* Soket basi dari proses yang mati diganti; soket yang masih dijawab, atau berkas biasa di jalur itu, tidak pernah ditimpa.

## 3. Resep otomasi

Resep adalah berkas JSON di `~/.config/sorot/automation/*.json`:

```json
{"name": "Mulai rekaman", "description": "Dari awal, tunggu 3 detik, gulir.", "confirm": true,
 "steps": [{"cmd": "reset"}, {"cmd": "show"}, {"cmd": "wait", "seconds": 3}, {"cmd": "play"}]}
```
Langkah yang boleh: `show` (tampil, dijeda), `hide`, `play`, `pause`, `toggle`, `reset`, `speed` (`steps` −10..10), `wait` (`seconds` 0,1..30). Maksimal 20 langkah dan 120 detik tunggu. Isian lain ditolak. `confirm: true` (bawaan) menampilkan dialog dengan seluruh langkah sebelum berjalan; resep yang ditolak validasi muncul sebagai peringatan, bukan galat.

### Menyusun resep dengan model lokal
Ketik satu kalimat ("mulai dari awal, tunggu tiga detik, lalu gulir pelan") dan tekan **Usulkan resep dengan AI lokal**. Model **hanya mengusulkan**:
* hanya server **lokal** yang dipakai (layanan jarak jauh ditolak untuk fitur ini), dan yang dikirim hanya kalimat itu, bukan naskah;
* balasan lolos validator yang sama dengan resep tulisan tangan, jadi langkah di luar daftar tidak mungkin lolos;
* usulan baru disimpan setelah Anda menekan **Simpan**, dan resep hasil model selalu `confirm: true`.

## 4. `sorot --doctor`

Daftar periksa hanya-baca: versi, keluarga distro, sandbox Flatpak dan izin jaringannya, server LLM lokal, alat kontainer (hanya dicari di `PATH`, tidak dijalankan), resep kontainer, soket kontrol, dan resep. `--offline` melewatkan pencarian port. Setiap temuan "perhatian" disertai langkah berikutnya.

## 5. Flatpak

Manifes dibuat oleh `make flatpak` (`scripts/build-flatpak.sh`). Izin yang diminta: jendela (X11/Wayland, DRI), `--share=ipc`, **`--share=network`** (layanan AI opsional dan server LLM di `127.0.0.1`, karena sandbox berbagi jaringan dengan host), dan layanan kunci (`org.freedesktop.secrets`). Tes memastikan tidak ada izin di luar daftar itu. Folder rumah **tidak** dibuka: Buka/Simpan lewat portal. Google Drive (rclone) tidak tersedia di sandbox.

## Yang belum dibuktikan
* **Tidak ada build Flatpak yang pernah dijalankan** dan tidak ada kontainer yang pernah dinyalakan: lingkungan pembuatan tidak punya remote Flatpak, daemon kontainer, atau akses ke Flathub/registry. Yang terbukti: manifes diterima `flatpak-builder --show-manifest`; resep compose lolos `docker compose config` dan tes aturan; seluruh logika (penemuan server, soket, resep, planner) diuji terhadap server palsu lokal.
* Dugaan yang perlu dicek di mesin sungguhan: soket di `$XDG_RUNTIME_DIR/app/<ID>/` terlihat dari `sorotctl` di luar sandbox; Orca dan portal berjalan baik di Flatpak; nama dan tag citra kontainer, serta dukungan GPU tertentu.
* Model lokal sungguhan tidak dijalankan di sini; kualitas usulan resep bergantung pada model dan selalu perlu Anda baca.
