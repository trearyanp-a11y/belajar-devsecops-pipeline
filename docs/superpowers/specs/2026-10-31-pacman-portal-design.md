# Portal login dan Pac-Man

Pengguna menyetujui penggabungan login dan Pac-Man serta penyesuaian UI pada 31 Oktober 2026. Implementasi dikerjakan langsung dalam sesi ini.

## Rancangan

- Satu aplikasi Flask, repo, image dan Deployment K3s yang sudah ada. Dua pod memakai PVC `/data/users.db`; tabel `users` dipertahankan, tabel `scores` ditambahkan secara idempoten.
- `/` menjadi portal login bergaya arcade gelap dengan aksen kuning dan cyan. Login valid membuat session dan mengarahkan ke `/game`. Tanpa session, halaman game kembali ke login dan API mengembalikan 401. Logout menggunakan POST.
- Flask signed cookie menggunakan kunci acak yang sama dari Secret `flask-session` pada kedua pod. Cookie HttpOnly, SameSite=Lax, masa berlaku 8 jam. Secure dapat diaktifkan ketika HTTPS tersedia; lab tetap memakai HTTP NodePort.
- Semua POST menggunakan token CSRF. Nama pada skor berasal dari session, bukan payload. Query login, skor dan pencarian menggunakan parameter binding; password tetap hash. Nilai skor dan durasi dibatasi serta harus berupa angka terbatas yang valid.
- Game dan kontrol yang ada digunakan kembali. Portal responsif, memiliki label input, kesalahan yang jelas, fokus keyboard, tombol tampilkan password dan dukungan reduced motion. Status CI palsu di antarmuka game dihapus.
- Delapan skor Pac-Man lokal diperiksa dan dipertahankan saat integrasi; data akun tidak direset. Tidak ada database, secret atau backup baru yang masuk Git.
- Pipeline Semgrep, Pylint, pip-audit, Trivy dan distribusi image tidak diubah kebijakannya. Docker memasukkan aset statis. Diagram dan catatan ujian diperbarui.

## Bukti penerimaan

Tes database nyata membuktikan migrasi idempoten, login/logout, pembatasan akses, penolakan SQL injection/CSRF dan validasi skor. Browser membuktikan login menuju game, kontrol game, pencarian dan tampilan desktop/mobile. Pipeline aman harus lolos dan image yang sama dideploy; contoh SQL rentan hanya untuk gate gagal pada branch demo.

## Batas

SQLite pada satu VM bukan HA antar-node. Skor dihitung browser sehingga belum merupakan sistem anticurang. Tidak menambah registrasi, OAuth, layanan terpisah atau dependency aplikasi. Commit hanya memakai identitas Git pengguna, tanpa atribusi asisten; main tidak digabung otomatis.
