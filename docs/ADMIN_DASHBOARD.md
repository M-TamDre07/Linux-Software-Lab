# Admin Control Room

## Tujuan dan batas akses

Route privat website adalah **/admin/**. Halaman ini menggunakan Supabase Auth untuk login dan Row Level Security (RLS) untuk memeriksa akses di database. Menyembunyikan elemen UI bukan kontrol keamanan; semua kueri harus tetap aman bila dipanggil langsung melalui Data API.

Dashboard versi pertama menyediakan ringkasan jumlah entri, jumlah yang dipublikasikan/tersembunyi, waktu sinkronisasi terakhir, pencarian, tampilan record JSON, dan ekspor JSON. Ini adalah dashboard inspeksi read-only untuk seluruh katalog yang diizinkan bagi maintainer. Tidak ada operasi tulis katalog dari browser.

## Mengapa mirror katalog read-only

Sumber resmi katalog adalah **public/data/software.json** di GitHub. GitHub Actions menyalin konten tersebut ke **public.software_catalog** dan melakukan verifikasi setelah sinkronisasi. Jika panel mengubah data mirror langsung, perubahan dapat hilang saat sinkronisasi berikutnya. Karena itu perubahan katalog dibuat ke sumber GitHub melalui proses review, kemudian workflow menyinkronkannya ke Supabase.

Untuk mengubah katalog, buka file sumber di GitHub dari dashboard. Setelah perubahan masuk ke main, workflow Supabase Catalog Sync memvalidasi dan menyinkronkan data jika secret CI telah dikonfigurasi.

## Menyiapkan akun maintainer pertama

1. Buka Supabase Dashboard → Authentication → Users dan buat akun untuk maintainer. Pendaftaran publik tidak dibuka dari halaman admin.
2. Salin UUID akun tersebut.
3. Jalankan query berikut melalui SQL Editor proyek Linux-Software-Lab. Ganti placeholder UUID dengan ID yang benar.

    insert into public.lsl_admin_users (user_id, active, note)
    values ('<UUID-AKUN-SUPABASE>', true, 'Project owner')
    on conflict (user_id) do update
      set active = excluded.active,
          note = excluded.note;

4. Buka /admin/ dan login dengan email/password akun tersebut.
5. Untuk mencabut akses, ubah active menjadi false atau hapus baris akun itu dari SQL Editor.

Jangan memberikan hak INSERT/UPDATE/DELETE pada tabel izin admin kepada pengguna authenticated. Provisioning dan pencabutan akses dilakukan oleh pemilik proyek lewat alat tepercaya. Pengguna yang berhasil login tetapi belum terdaftar akan melihat UUID miliknya sendiri dan tidak akan mendapat data katalog.

## Model keamanan

- Tabel public.lsl_admin_users memiliki RLS aktif. Pengguna authenticated hanya bisa membaca baris dengan user_id sama dengan auth.uid().
- Baris katalog yang belum dipublikasikan hanya terlihat kepada pengguna authenticated yang tercatat aktif di lsl_admin_users.
- Pengunjung anonim tetap hanya mendapat SELECT untuk baris published = true.
- Pengguna browser tidak mendapatkan hak tulis katalog atau tabel daftar admin.
- Supabase publishable key pada aset publik memang bukan secret; keamanan ditentukan oleh SQL grants, RLS, dan Auth. Jangan pernah meletakkan sb_secret_ atau service-role key di HTML, JavaScript publik, atau environment variable dengan prefix browser-public.
- Halaman memakai noindex/nofollow dan tidak dimasukkan ke sitemap. Itu membantu privasi navigasi, tetapi bukan mekanisme otorisasi.

## Validasi dan troubleshooting

- Bila login gagal, periksa user di Authentication → Users, status konfirmasi email, serta provider Email.
- Bila sistem tidak dapat memeriksa akses admin, verifikasi migration add_admin_catalog_read_access dan policy RLS pada tabel izin.
- Bila query katalog mengembalikan error Data API, periksa grant SELECT untuk authenticated, status API, dan RLS. Jangan memperbaiki error dengan memberi akses tabel kepada semua pengunjung.
- Bila waktu sinkronisasi tertinggal, buka workflow Supabase Catalog Sync. Pastikan repository secret SUPABASE_SECRET_KEY berisi key server modern sb_secret_ yang disimpan langsung di GitHub Actions Secrets. Key publishable bukan pengganti secret CI.
- Setelah perubahan SQL, jalankan Supabase Security Advisor dan verifikasi bahwa pengguna anonim tidak dapat membaca baris tidak dipublikasikan atau menulis tabel.

## Evolusi berikutnya

Jika nanti dibutuhkan CRUD lewat dashboard, tetapkan satu sumber data yang otoritatif terlebih dahulu. Pilihan yang konsisten ialah backend tepercaya membuat Pull Request ke GitHub, atau migrasi penuh menjadikan Supabase sumber utama dan memperlakukan file JSON sebagai hasil build. Jangan mengaktifkan edit langsung ke mirror selama GitHub tetap menjadi sumber utama.
