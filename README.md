# Belajar DevSecOps Pipeline

Aplikasi demonstrasi login Flask untuk ujian DevSecOps. Pipeline menjalankan
empat gerbang CI paralel, membangun dan memindai satu image, lalu mengirim image
yang sama ke K3s di VM Ubuntu. Dua pod berbagi SQLite pada PVC.

## Arsitektur dan akses

- Windows/developer -> GitHub Actions.
- CI: Semgrep, Pylint + regression tests, pip-audit, Trivy filesystem.
- Build + Trivy image -> artifact TAR dan SHA256 -> self-hosted runner yan.
- Runner mengimpor artifact ke containerd, tanpa membangun ulang image.
- Image ditandai SHA commit; /about mengembalikan revision untuk verifikasi.
- K3s satu node 192.168.15.151, dua replika, NodePort 30050 -> port 5000.
- Database /data/users.db pada PVC flask-pvc 1Gi, local-path, ReadWriteOnce.
- Login mengecek hash password dengan parameterized query.
- Gunicorn berjalan sebagai UID 1000 dengan filesystem root read-only.
- Readiness /health memeriksa database; liveness /live memeriksa proses.
- Diagram: [JPG](docs/diagram_pipeline.jpg), [Mermaid](docs/pipeline.mmd).

URL laboratorium:
- http://192.168.15.151:30050/
- http://192.168.15.151:30050/health
- http://192.168.15.151:30050/about

Ini aplikasi demonstrasi verifikasi kredensial, belum menyediakan sesi login
atau halaman terlindungi. HTTP NodePort ditujukan untuk jaringan lab; HTTPS
diperlukan jika akan dipublikasikan. Dua pod di satu VM bukan HA antar-node.

## Menjalankan lokal di Windows

Gunakan Python 3.11 atau 3.12; CI dan container memakai 3.12.
Gunicorn digunakan dalam container Linux, bukan Windows.

    python -m venv .venv
    .venv\Scripts\python -m pip install -r requirements.txt
    .venv\Scripts\python -c "import getpass,os; os.environ['ADMIN_PASSWORD']=getpass.getpass('Password admin lokal: '); from app import app,init_db; init_db(); app.run()"

Buka http://127.0.0.1:5000. Akun default bernama admin; password baru diminta
untuk database kosong. Jangan commit file database, .env, atau password.

    .venv\Scripts\python -B -m unittest discover -s tests -v

Empat tes deployment shell dilewati di Windows dan dijalankan di CI Linux.
CI memakai Pylint 4.1.1 dengan ambang 9.0 pada app.py dan wsgi.py.

## Provisioning dan migrasi database

Pada instalasi baru, buat Secret sebelum deployment. Input berikut tidak
menaruh password pada argumen CLI atau history:

    read -rsp 'Password admin awal: ' ADMIN_PASSWORD; echo
    printf '%s' "$ADMIN_PASSWORD" | sudo k3s kubectl create secret generic flask-admin --from-file=password=/dev/stdin --dry-run=client -o yaml | sudo k3s kubectl apply -f -
    unset ADMIN_PASSWORD

Nama admin default bisa diubah melalui ADMIN_USERNAME pada lingkungan aplikasi.
Setelah database berisi akun, startup mempertahankan akun yang sudah ada dan
tidak mereset password dari Secret.

Untuk deployment lama yang memakai /app/users.db di setiap pod:
1. Cadangkan database masing-masing pod memakai SQLite backup API.
2. Bandingkan data. Jika berbeda, rekonsiliasikan terlebih dahulu; jangan pilih
   salah satu salinan secara diam-diam.
3. Buat flask-pvc dan gunakan pod sementara UID 1000 untuk menyalin database
   hasil pemeriksaan ke /data/users.db sebelum mengubah Deployment.
4. Periksa PRAGMA integrity_check dan jumlah akun.
5. Jalankan deployment baru. init_db memakai BEGIN IMMEDIATE, mengubah password
   plaintext menjadi hash satu kali, dan menandai PRAGMA user_version=1.
6. Verifikasi akun lama tetap dapat login dan kedua pod membaca PVC yang sama.

Pada VM lab, pencadangan dan penyalinan awal telah dipersiapkan di:
 /home/yan/pipeline-backups/20261030-184611
Direktori backup 0700 dan file DB 0600. Backup tersebut masih mengandung data
legacy sensitif; simpan hanya pada VM, jangan unggah ke GitHub.

Migrasi menutup setiap koneksi secara eksplisit. Startup paralel diserialisasi.
SQLite tetap memiliki batas satu penulis; local-path hanya untuk satu node.

## Workflow dan kebijakan deployment

Trigger:
- Push ke main/master: CI lalu deployment bila seluruh gerbang lolos.
- Pull request ke main/master: CI saja, deployment skipped.
- workflow_dispatch: CI dan deployment pada branch yang dipilih secara eksplisit
  oleh pengguna yang memiliki izin menjalankan workflow.

Langkah image:
1. Build secure-flask-app:<SHA> dengan APP_REVISION=<SHA>.
2. Trivy memindai image tersebut: CRITICAL, ignore-unfixed=true.
3. Export image yang lolos menjadi image.tar dan image.tar.sha256.
4. Upload/download artifact pada run yang sama.
5. scripts/deploy.sh memeriksa checksum, mengimpor image, menerapkan manifest
   dengan tag SHA, menunggu rollout, dan memeriksa HTTP serta revision.

Kebijakan scan image tersebut tidak berarti nol kerentanan. Trivy filesystem
memblokir HIGH/CRITICAL; aturan dan database CVE dapat berubah.
Image dasar, dependensi aplikasi, dan action refs dipin. Ruleset Semgrep
p/python, p/secrets, p/dockerfile dan database kerentanan tetap diperbarui
oleh penyedianya; metrics Semgrep dinonaktifkan.

Secret aplikasi tidak disimpan dalam source. Runner tidak memerlukan token
GitHub pribadi pada workflow; artifact ditangani oleh token run.
Akses sudo k3s tetap merupakan hak kuat yang harus dibatasi pada runner tepercaya.

## Demonstrasi ujian gagal -> perbaikan -> sukses

Gunakan branch demo dan simpan SHA aman. GitHub UI: Actions -> workflow ini ->
Run workflow -> pilih branch demo. Push branch demo tidak otomatis memicu
workflow karena filter push hanya main/master.

1. Pastikan baseline lulus; catat SHA aman dengan git rev-parse HEAD.
2. Buat perubahan sengaja gagal pada app.py, misalnya tambahkan sintaks Python
   tidak lengkap. Commit dengan git add app.py, lalu push branch demo.
3. Jalankan workflow manual. Tunjukkan quality gate merah, pesan kegagalan,
   dan image/deployment skipped. Aplikasi lama tetap dapat diakses.
4. Pulihkan dengan git restore --source=<SHA_AMAN> -- app.py.
5. Periksa diff, jalankan regression tests/Pylint, commit perbaikan dan push.
6. Jalankan workflow manual lagi. Tunjukkan enam job sukses dan runner yan.
7. Cocokkan /about.revision, tag image Deployment, dan SHA run.
8. Tunjukkan dua pod Ready, PVC Bound, dan halaman web.

Skenario sintaks rusak membuktikan quality gate. Jika ingin membuktikan SAST,
gunakan perubahan SQL tidak terparameterisasi dan tunjukkan rule Semgrep yang
benar-benar mendeteksinya. Jangan menyebut kegagalan sintaks sebagai temuan SQLi.

Perintah pemeriksaan pada VM:

    sudo k3s kubectl get nodes -o wide
    sudo k3s kubectl get deployment,pods,svc,pvc -o wide
    sudo k3s kubectl rollout status deployment/flask-app --timeout=180s
    curl --fail --show-error http://192.168.15.151:30050/health
    curl --fail --show-error http://192.168.15.151:30050/about

Periksa namespace default. Jangan menggunakan rollout restart untuk mengganti
image: tag per commit pada manifest sudah membuat perubahan image eksplisit.

## Pemulihan

- Kode baru bisa dikembalikan ke image SHA sebelumnya yang sudah mendukung schema
  hash. Image tag tetap harus tersedia pada containerd node.
- Kode legacy sebelum migrasi tidak memahami password hash. Untuk kembali ke
  kode legacy diperlukan database backup legacy yang sesuai, bukan sekadar
  kubectl rollout undo terhadap database yang telah dimigrasikan.
- Jangan menghapus PVC sebagai langkah troubleshooting.
- Backup SQLite sebelum pengujian migrasi/restore. Backup PVC local-path masih
  berada pada disk VM dan tidak menggantikan backup di media lain.

## Proyek Pac-Man

Proyek Pac-Man berada di folder saudara dan belum menjadi aplikasi ujian aktif.
Jika nanti keduanya dijalankan bersamaan, pakai NodePort berbeda dari 30050 untuk
game, integrasikan repo/runner, dan jangan biarkan app_broken.py ikut cakupan
source sukses. Perbaikan ini memusatkan deployment pada aplikasi login.

## Dokumentasi teknis

- https://flask.palletsprojects.com/en/stable/deploying/gunicorn/
- https://docs.python.org/3/library/sqlite3.html#how-to-use-the-connection-context-manager
- https://docs.github.com/en/actions/tutorials/store-and-share-data
