# CV Detection — Experiment Log

Setiap eksperimen didokumentasikan dengan: apa yang diubah, hipotesis (kenapa perubahan ini diharapkan membantu), konfigurasi, hasil, dan pelajaran yang diambil. Tujuannya supaya progres model bisa ditelusuri dan dijelaskan saat interview — bukan cuma "angkanya naik", tapi "kami ubah X karena Y, dan hasilnya membuktikan/membantah hipotesis itu".

Semua run dijalankan di Apple M4 (CPU-only, tidak ada CUDA GPU) — dicatat karena ini berpengaruh signifikan ke waktu training dan jadi pertimbangan trade-off (imgsz, batch size, epoch budget).

---

## v1 — Baseline dua kelas (Airplane vs Truncated_airplane)

**Tanggal:** 2026-08-17
**Command:**
```
uv run yolo detect train data=data/yolo/data.yaml model=yolov8n.pt \
  imgsz=1280 epochs=60 batch=4 patience=15 seed=42 name=aircraft_baseline
```

**Setup data:** 103 citra satelit (2560x2560px), 3425 instance, 2 kelas asli dari dataset (`Airplane`, `Truncated_airplane` — pesawat yang terpotong tepi tile citra). Split 72/15/16 (train/val/test), stratifikasi acak (bukan per-kelas — lihat "Pelajaran" di bawah).

**Hipotesis awal:** Model bisa belajar membedakan pesawat utuh vs terpotong dari data yang ada.

**Hasil (test set, 16 gambar):**

| Kelas | Instances | Precision | Recall | mAP50 | mAP50-95 |
|---|---|---|---|---|---|
| Airplane | 385 | 0.988 | 0.930 | **0.931** | 0.674 |
| Truncated_airplane | 9 | 1.000 | 0.000 | **0.012** | 0.005 |
| **all (rata-rata)** | 394 | 0.994 | 0.465 | 0.472 | 0.339 |

Training berhenti otomatis di epoch 56/60 (early stopping, `patience=15` — mAP50 keseluruhan plateau di ~0.466-0.468 sejak epoch ~35). Total waktu: 44 menit.

**Pelajaran:**
1. **Class imbalance fatal untuk kelas minoritas.** `Truncated_airplane` cuma 9 instance di test set (dan proporsi serupa di train) — recall 0.0 berarti model tidak pernah berhasil mendeteksinya sama sekali. Ini bukan kegagalan model, ini kesalahan desain split/kelas: dengan data sesedikit ini, kelas dengan <30-an instance nyaris mustahil dipelajari dengan baik.
2. **mAP rata-rata itu angka yang menipu kalau tidak dipecah per kelas.** Overall mAP50=0.472 terlihat biasa saja, tapi kelas utama (`Airplane`, yang sebenarnya jadi target deteksi utama untuk use case collision/positioning) sudah mencapai 0.931 — jauh melebihi target 0.7 di project breakdown. Kalau kita cuma lapor angka rata-rata, kita salah menilai model sendiri sebagai "kurang bagus" padahal sebenarnya sudah sangat baik untuk tugas yang relevan.
3. **Pertanyaan mendasar: apakah 2 kelas ini valid secara semantik untuk use case kita?** `Truncated_airplane` bukan properti fisik pesawat, itu artefak dari cara citra di-tile jadi 2560x2560. Untuk collision detection & space optimization di hangar, kita cuma butuh tahu "ada pesawat di sini, dengan bounding box ini" — status "terpotong tepi citra" tidak relevan sama sekali dengan geometri pesawat sesungguhnya. Keputusan desain di v1 (mewarisi label kelas dataset mentah-mentah) adalah keputusan yang keliru untuk use case ini, bukan cuma masalah data.

→ **Keputusan untuk v2:** merge kedua kelas jadi satu (`Airplane`). Ini bukan trik menaikkan angka metrik — ini koreksi terhadap task definition yang salah di v1.

---

## v2 — Merge jadi single-class (`Airplane`)

**Tanggal:** 2026-08-17
**Command:**
```
uv run yolo detect train data=data/yolo/data.yaml model=yolov8n.pt \
  imgsz=1280 epochs=80 batch=4 patience=20 seed=42 name=aircraft_merged
```

**Perubahan dari v1:** `scripts/prepare_yolo_dataset.py` — `CLASS_TO_ID` memetakan `Airplane` dan `Truncated_airplane` ke class_id yang sama (0). Semua konfigurasi training lain identik dengan v1 (imgsz, batch, seed, model dasar), kecuali `epochs`/`patience` dinaikkan sedikit (80/20 vs 60/15) untuk memberi ruang lebih karena dataset efektif per-kelas kini lebih besar.

**Hipotesis:** Menyatukan kelas akan (a) menghilangkan masalah recall=0 pada kelas minoritas karena semua instance sekarang berkontribusi ke satu kelas dengan ~3425 instance, dan (b) mAP50 keseluruhan akan mendekati angka kelas `Airplane` di v1 (~0.93), karena secara task itu memang tugas yang sama — deteksi "ada pesawat" — hanya sekarang direpresentasikan dengan benar.

**Hasil (test set, 16 gambar):**

| Kelas | Instances | Precision | Recall | mAP50 | mAP50-95 |
|---|---|---|---|---|---|
| **Airplane (single-class)** | 394 | 0.989 | 0.916 | **0.932** | 0.671 |

Training berjalan penuh 80/80 epoch (tidak early-stop — masih ada perbaikan kecil sampai akhir), total 1 jam 9 menit. mAP50 plateau di kisaran 0.917-0.923 sejak sekitar epoch 42, dengan perbaikan marginal terus sampai epoch terakhir.

**Perbandingan langsung ke v1:**

| Metric | v1 (kelas `Airplane` saja) | v2 (single-class) |
|---|---|---|
| Precision | 0.988 | 0.989 |
| Recall | 0.930 | 0.916 |
| mAP50 | 0.931 | 0.932 |
| mAP50-95 | 0.674 | 0.671 |

**Hipotesis terkonfirmasi:** performa v2 secara statistik setara dengan performa kelas `Airplane` di v1 (selisih dalam margin noise, bukan perbedaan berarti) — **membuktikan bahwa menyatukan kelas tidak kehilangan informasi yang berguna**, karena `Truncated_airplane` memang bukan target deteksi yang berbeda secara semantik. Bedanya krusial: angka 0.932 di v2 adalah angka yang **jujur mewakili seluruh model**, sedangkan mAP rata-rata v1 (0.472) menyesatkan karena didominasi kegagalan kelas yang secara desain memang tidak seharusnya ada.

**Observasi tambahan — konvergensi lebih cepat:** Di epoch 7, v2 sudah mencapai mAP50 0.844, sementara v1 baru mencapai ~0.38 di epoch 3 dan ~0.46 di epoch 15 (dan itu pun angka rata-rata yang sudah "dibantu" turun oleh kelas minoritas). Ini konsisten dengan hipotesis bahwa model v1 menghabiskan kapasitas belajar untuk kelas yang pada akhirnya tidak pernah berhasil dipelajari.

**Pelajaran:** Perbaikan task definition (v1→v2) memberi dampak yang jelas dan besar (recall kelas minoritas 0.0 → hilang sepenuhnya sebagai masalah), sementara metrik kelas utama nyaris tidak berubah — ini memperkuat argumen di `cv-methodology.md` bahwa bottleneck saat ini bukan lagi soal definisi task (sudah benar sejak v2), melainkan soal jumlah & resolusi data. Mendukung keputusan lanjut ke v3a (tiling) sebagai prioritas berikutnya, bukan model lebih besar.

---

## v3 (rencana) — kandidat perbaikan, dievaluasi satu per satu

Dua ide yang dipertimbangkan setelah v2 selesai — **tidak diasumsikan otomatis membantu**, masing-masing punya alasan teknis dan risiko sendiri (lihat `docs/cv-methodology.md` bagian "Rencana Iterasi Berikutnya" untuk analisis lengkap):

1. **Tiling citra** (2560x2560 → beberapa crop, misal 1280x1280 atau 640x640) — prioritas lebih tinggi. Alasan: saat ini `imgsz=1280` memaksa YOLO mengecilkan citra asli 2x sebelum training, yang berarti pesawat (sudah relatif kecil, puluhan-ratusan piksel) menyusut lebih jauh. Tiling mempertahankan resolusi piksel asli per pesawat sekaligus melipatgandakan jumlah sampel training secara riil (bukan duplikasi/augmentasi kosmetik).
2. **Model lebih besar (yolov8s)** — prioritas lebih rendah, hasilnya lebih tidak pasti. Precision/recall v1 pada kelas Airplane sudah tinggi (0.988/0.93) dengan yolov8n, mengindikasikan bottleneck saat ini kemungkinan besar bukan kapasitas model, melainkan jumlah data (72 gambar training). Menambah parameter tanpa menambah data berisiko overfitting, bukan otomatis perbaikan.

Rencana: jalankan v3a (tiling) dulu sebagai eksperimen terpisah dari v3b (yolov8s), supaya efek masing-masing bisa diisolasi dan dibandingkan langsung ke v2 sebagai baseline — bukan digabung sekaligus sehingga tidak jelas mana yang berkontribusi.
