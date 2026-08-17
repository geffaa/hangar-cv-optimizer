# Metodologi Computer Vision — Kenapa YOLO, Kenapa Konfigurasi Ini

Dokumen ini menjelaskan alasan teknis di balik pilihan arsitektur, versi model, dan metode training untuk komponen deteksi pesawat (`hangar_cv_optimizer.cv`). Ditulis supaya setiap keputusan bisa dipertanggungjawabkan, bukan sekadar "karena tutorial pakai ini".

## 1. Definisi Masalah

Task: given citra (top-down/aerial atau nantinya CCTV hangar), temukan **semua pesawat dan bounding box-nya**. Ini adalah **object detection** klasik — bukan classification (kita tidak cuma butuh tahu "ada pesawat di foto ini", tapi di mana persisnya, karena output ini jadi input untuk collision-check dan space-optimization service), dan bukan segmentation (kita tidak butuh mask piksel-per-piksel; bounding box/polygon sederhana sudah cukup untuk representasi geometris di `AircraftFootprint`).

Karakteristik data yang relevan untuk pemilihan metode:
- Objek relatif kecil dibanding ukuran citra (pesawat menempati puluhan-ratusan piksel dari citra 2560x2560).
- Banyak objek per citra (rata-rata ~33 instance/gambar di dataset kita — bandara/apron padat).
- Orientasi bervariasi (pesawat bisa menghadap arah mana saja, tidak seperti foto objek studio).
- Perlu inference cepat, karena nantinya dipanggil sebagai bagian dari API request/response (bukan batch job semalaman).

## 2. Kenapa One-Stage Detector (YOLO family), Bukan Two-Stage (Faster R-CNN dkk)

| | Two-stage (Faster R-CNN, Mask R-CNN) | One-stage (YOLO, SSD, RetinaNet) |
|---|---|---|
| Cara kerja | Region Proposal Network dulu usulkan kandidat box, baru diklasifikasi tahap kedua | Prediksi bbox + class langsung dalam satu forward pass |
| Akurasi (umum) | Sedikit lebih tinggi di beberapa benchmark, terutama objek kecil/padat | Kompetitif, gap makin kecil di versi modern (v8+) |
| Kecepatan inference | Lebih lambat (dua tahap) | Jauh lebih cepat, real-time capable |
| Kompleksitas training | Lebih rumit (banyak hyperparameter RPN) | Lebih sederhana, satu loss function terpadu |

**Keputusan: YOLO.** Alasan konkret untuk case ini:
1. **Kecepatan relevan langsung ke arsitektur produk.** Breakdown project menempatkan CV detection sebagai satu service dalam alur `upload → detect → optimize → validate`, dipanggil lewat REST API. Latency yang predictable dan rendah (YOLO: puluhan-ratusan ms per gambar) jauh lebih cocok untuk pola request-response dibanding two-stage detector yang bisa detik-an per gambar, apalagi berjalan di CPU (tidak ada GPU di environment development ini).
2. **Gap akurasi dengan Faster R-CNN untuk objek sekelas pesawat di citra aerial sudah sangat tipis di YOLOv8+** — YOLOv8 menggunakan anchor-free detection head dan multi-scale feature pyramid (mirip FPN yang dulu jadi keunggulan two-stage), jadi keunggulan akurasi two-stage untuk objek kecil sudah banyak terkompensasi.
3. **Ekosistem tooling.** Ultralytics (pengelola YOLOv8) menyediakan CLI/Python API yang sudah menangani augmentasi (mosaic, HSV jitter, dll), format konversi, dan evaluasi (mAP per kelas) out-of-the-box — mengurangi permukaan bug untuk project dengan timeline terbatas, tanpa mengorbankan kemampuan menjelaskan cara kerja di baliknya.

## 3. Kenapa YOLOv8 (bukan v5, v9, v10, v11, atau RT-DETR)

Per Agustus 2026, keluarga YOLO Ultralytics yang tersedia mencakup v5 (lama, masih dipakai luas), v8 (versi paling matang & terdokumentasi dengan baik), v9/v10/v11 (arsitektur lebih baru, klaim efisiensi lebih tinggi), dan RT-DETR (transformer-based, di luar keluarga YOLO tapi ditawarkan Ultralytics dengan API yang sama).

**Keputusan: YOLOv8**, dengan pertimbangan:
- **Kematangan & stabilitas dokumentasi** lebih tinggi dibanding v9/v10/v11 yang lebih baru — penting untuk debugging cepat saat resource development terbatas (CPU-only, tanpa GPU cloud).
- **Anchor-free head** (perbedaan besar dari v5) menyederhanakan tuning — tidak perlu menentukan anchor box preset yang cocok dengan rasio aspek pesawat, model belajar langsung regresi ke koordinat box.
- YOLOv9/v10/v11 menjanjikan efisiensi lebih baik di angka publikasi resminya, tapi keunggulan itu paling terasa di skala dataset besar (COCO-scale) — untuk dataset kecil (103 gambar) seperti kasus kita, pemilihan versi arsitektur bukan faktor pembatas utama (lihat Section 5: bottleneck kita adalah data, bukan model).
- RT-DETR (transformer) butuh data jauh lebih banyak untuk mengalahkan CNN-based detector pada dataset kecil — attention-based model umumnya punya inductive bias lebih lemah dibanding convolution, sehingga lebih rentan underfit/perlu lebih banyak data. Tidak cocok untuk dataset 103 gambar.

**Kenapa ukuran "nano" (`yolov8n`), bukan `s`/`m`/`l`/`x`:** Dimulai dari model terkecil (3.2M parameter) sebagai baseline, dengan alasan eksplisit di Section 5 — bukan sekadar "biar cepat", tapi hipotesis bahwa dataset sekecil ini lebih mungkin dibatasi oleh jumlah data daripada kapasitas model. Hasil v1/v2 (precision 0.988, recall 0.93 pada kelas utama) mengonfirmasi model nano saja sudah mampu mencapai performa tinggi — memvalidasi keputusan mulai dari model terkecil, bukan asal tebak.

## 4. Kenapa `imgsz=1280` (bukan default 640)

Citra sumber berukuran 2560x2560px. Default YOLOv8 (`imgsz=640`) akan mengecilkan citra 4x — pesawat yang di resolusi asli berukuran ~80-150px bisa menyusut jadi ~20-40px, mendekati batas bawah yang bisa dideteksi reliable oleh detector modern (objek <32px sering dikategorikan "small object" dalam literatur COCO dan secara empiris punya recall lebih rendah).

`imgsz=1280` adalah kompromi: mengurangi downscaling jadi 2x (bukan 4x), sambil tetap dalam batas resource yang wajar untuk training CPU-only (ukuran lebih besar dari itu, misal training di resolusi native 2560, akan sangat lambat tanpa GPU dan berisiko out-of-memory).

## 5. Bottleneck Saat Ini: Data, Bukan Model — dan Implikasinya ke Rencana Iterasi

Ini poin paling penting untuk dijelaskan jujur, bukan cuma diklaim.

**Bukti:** Pada v1, kelas `Airplane` (385 instance test) mencapai precision 0.988 dan recall 0.930 — model yolov8n dengan hanya 3.2M parameter sudah mendekati batas atas realistis (precision/recall di atas 0.9 keduanya) untuk task ini. Sementara kelas `Truncated_airplane` (9 instance test) gagal total (recall 0.0) BUKAN karena model kurang canggih, tapi karena hampir tidak ada contoh untuk dipelajari.

**Implikasi:** Kalau bottleneck adalah kapasitas model, solusinya adalah model lebih besar. Kalau bottleneck adalah kuantitas/kualitas data, model lebih besar dengan data tetap sama justru berisiko **overfitting** (model punya kapasitas "menghafal" 72 gambar training, bukan generalisasi). Bukti di atas mengarah ke yang kedua.

**Rencana Iterasi Berikutnya (v3), diurutkan berdasar keyakinan bahwa itu benar-benar akan membantu:**

1. **Tiling citra (prioritas tinggi, tingkat keyakinan tinggi).** Memotong tiap citra 2560x2560 jadi beberapa tile (misal 4x tile 1280x1280, atau 16x tile 640x640) sebelum training, alih-alih mengecilkan (downscale) satu citra utuh. Ini menyerang dua masalah sekaligus secara langsung:
   - **Resolusi piksel per pesawat tetap terjaga** (tidak ada downscaling sama sekali kalau tile size = imgsz), langsung mengatasi masalah "small object shrinks further" di Section 4.
   - **Jumlah sampel training riil bertambah** (72 gambar → ratusan tile), yang secara langsung mengurangi risiko overfitting yang jadi kekhawatiran di atas — ini bukan augmentasi kosmetik (seperti flip/rotate yang menghasilkan variasi dari data yang sama), tapi benar-benar menyajikan detail piksel yang sebelumnya hilang karena downscaling.
   - Trade-off yang harus diwaspadai: pesawat yang berada di garis potong tile akan terpotong (memunculkan lagi masalah "truncated object" yang baru saja kita hindari di v2) — perlu strategi overlap antar tile atau aturan minimum visible area supaya tidak menciptakan ulang masalah class-imbalance dari sisi lain.

2. **Model lebih besar, `yolov8s` (prioritas lebih rendah, tingkat keyakinan sedang-rendah).** Dicoba SETELAH tiling, bukan sebagai pengganti — supaya kalau ada perbaikan, jelas atribusinya ke tiling vs ke ukuran model (lihat `EXPERIMENTS.md` v3a/v3b, dijalankan sebagai eksperimen terpisah). Ekspektasi jujur: berdasar analisis bottleneck di atas, kemungkinan besar dampaknya kecil atau bahkan negatif (overfitting) selama dataset masih di kisaran ratusan gambar — akan diverifikasi secara empiris, bukan diasumsikan.

Pendekatan yang SENGAJA TIDAK dipilih di titik ini: menambah epoch tanpa batas (sudah terbukti plateau/early-stop di v1 dan kemungkinan besar v2 juga — nambah epoch pada data yang sama tidak mengatasi akar masalah), atau ganti ke arsitektur yang jauh lebih besar (yolov8l/x) yang jelas berisiko overfit parah pada 72 gambar training.

## 6. Kaitan ke Use Case Starlight Hangars

Pemilihan tiap keputusan di atas secara eksplisit mengikuti constraint dari deskripsi kerja: "computer vision... to optimize aircraft positioning... and monitor for hangar collisions" — bukan riset akademik untuk mengejar SOTA mAP di benchmark publik. Prioritasnya:
- Output deteksi (bounding box) langsung dikonsumsi sebagai `AircraftFootprint` oleh service collision-check & optimization (lihat `docs-portfolio-idea` breakdown Section 3, arsitektur 3-service) — jadi metrik yang paling relevan adalah recall & precision pada kelas objek utama (pesawat), bukan mAP rata-rata yang bisa tersamarkan oleh kelas sekunder yang tidak relevan secara operasional (Section "Pelajaran v1" di `EXPERIMENTS.md`).
- Latency inference harus kompatibel dengan pola penggunaan request-response API, bukan batch processing semalaman — mengarahkan pilihan ke one-stage detector sejak awal.
- Keputusan didokumentasikan dengan trade-off eksplisit (bukan cuma hasil akhir) karena ini yang biasanya ditanya saat technical interview: bukan "berapa mAP-nya", tapi "kenapa pilih ini, apa yang dicoba, apa yang gagal, apa alasannya".
