# Pac-Man Portal Implementation Plan

> **For agentic workers:** Use executing-plans to implement this plan task-by-task.

**Goal:** Login wajib sebelum bermain Pac-Man, dengan portal arcade dan pipeline yang tetap terverifikasi.

**Architecture:** Gabungkan game yang sudah ada ke aplikasi login Flask. Signed session dari Secret bersama mengamankan halaman dan API; users dan scores memakai SQLite pada PVC yang sama.

**Tech Stack:** Flask, Werkzeug, SQLite, HTML/CSS/JavaScript, unittest, Gunicorn, GitHub Actions, K3s.

**Spec:** `docs/superpowers/specs/2026-10-31-pacman-portal-design.md`

## Global Constraints

- Pertahankan akun, hash password, delapan skor lama, dua pod dan NodePort 30050.
- Tidak menambah dependency aplikasi atau atribusi asisten pada commit.
- Secret tidak disimpan di Git; main tidak digabung otomatis.

## Review Focus

- Session harus berlaku pada kedua pod dengan satu key, dan gagal jika key berbeda.
- Payload list, boolean, NaN, infinity dan angka negatif tidak boleh masuk tabel skor.
- CSRF login, logout dan pengiriman skor wajib ditolak jika token hilang/salah.
- Nama akun berisi markup/SQL tetap data, tidak menjadi kode atau query.
- Perubahan DB tidak boleh menghapus akun/skor pada startup ulang/paralel.

## Task 1: Autentikasi dan skor

Files: `app.py`, `wsgi.py`, `tests/test_app.py`.

- [ ] Tambahkan tes untuk session/login/logout, akses game/API, CSRF, SQLi dan validasi skor. Jalankan tes dan pastikan gagal karena perilaku belum tersedia.
- [ ] Implementasikan guard request terpusat, signed session, token CSRF, tabel scores dan endpoint game/skor/pencarian. Pertahankan migrasi akun.
- [ ] Jalankan seluruh unittest dan Pylint; perbaiki sampai lolos.

## Task 2: UI dan deployment

Files: `templates/index.html`, `templates/game.html`, `static/css/style.css`, `static/js/game.js`, `static/js/portal.js`, `Dockerfile`, `k8s-deployment.yaml`.

- [ ] Gunakan aset game yang ada, buat portal arcade, hubungkan CSRF serta identitas akun dan perbaiki akses modal keyboard.
- [ ] Masukkan static ke image dan SECRET_KEY dari Secret wajib di manifest; provisioning key sekali tanpa mencetak nilainya.
- [ ] Uji browser desktop/mobile, login salah/benar, game, skor, pencarian dan logout. Jalankan tes Linux serta scan konfigurasi yang sama dengan CI.

## Task 3: Bukti dan pengiriman

Files: `README.md`, `docs/pipeline.mmd`, `docs/render_diagram.py`, Desktop `catatan_pipeline.txt`.

- [ ] Perbarui diagram dan petunjuk demonstrasi SQL gagal/perbaikan/sukses.
- [ ] Review diff, identitas commit dan hasil pengujian; commit/push branch fitur dengan identitas pengguna.
- [ ] Jalankan workflow branch fitur dan verifikasi revision, dua pod Ready, login/game serta data persisten. Catat hasil dan keterbatasan.
