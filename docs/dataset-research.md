# Riset Dataset — Perbandingan & Keputusan

Sebelum lanjut iterasi model, dilakukan riset terhadap dataset open-source lain untuk aircraft/airplane detection, untuk menjawab: apakah dataset Airbus Aircraft Detection yang dipakai sekarang ini pilihan terbaik yang realistis, atau ada yang lebih relevan untuk use case Starlight Hangars (positioning & collision detection di hangar/apron, bukan riset akademik citra satelit)?

## Tabel Perbandingan

| Dataset | Skala | Sudut Pandang | Anotasi | Akses & Lisensi | Relevansi ke Use Case Hangar |
|---|---|---|---|---|---|
| **Airbus Aircraft Detection** (dipakai sekarang) | 103 citra 2560x2560, 3425 bbox | Satelit top-down | Bbox | CC BY-NC-SA 4.0, akses langsung tanpa approval | Rendah-sedang — satelit murni, tapi ukuran manageable |
| RarePlanes | Real: 253 scene, ~14.7rb anotasi. Synthetic: 50rb citra, ~630rb anotasi | Satelit 30cm + atribut per pesawat (wingspan, role, kondisi) | Bbox + atribut, GeoJSON/COCO | CC BY-NC 4.0, via AWS Open Data (butuh akun AWS, gratis) | Sedang — tetap satelit, tapi atribut orientasi/dimensi relevan konseptual |
| DOTA (v1/v2) | 2.806 citra, 188.282 instance, 15-18 kelas | Aerial satelit, **oriented bbox (OBB)** | Polygon 4-titik | CC BY 4.0, mirror IEEE DataPort (perlu akun gratis) | Sedang — OBB relevan untuk estimasi orientasi pesawat |
| xView | 1.400 km², 1M+ instance | Satelit 0.3m GSD | Bbox horizontal | Gratis, registrasi wajib, ~20GB | Rendah — terlalu general-purpose & berat |
| HRPlanesv2 | 2.120 citra, 14.335 pesawat | Satelit/udara resolusi sangat tinggi | YOLO txt | Terbuka via Zenodo | Sedang — spesialis pesawat, bagus untuk augmentasi |
| iSAID | 2.806 citra (basis DOTA), 655.451 instance | Aerial, **instance segmentation** | Polygon mask | Non-commercial, perlu form request | Rendah-sedang — mask presisi tapi approval ribet |
| NWPU VHR-10 | 800 citra, 757 instance pesawat | Google Earth/Vaihingen | Bbox + mask | Gratis, mirror GitHub | Rendah — instance pesawat terlalu sedikit |
| DIOR | 23.463 citra, 192.472 instance, 20 kelas | Google Earth 800x800 | Bbox | Gratis via IEEE DataPort | Rendah-sedang — general-purpose, bukan spesialis pesawat |
| MAR20 | 3.842 citra, 22.341 instance, 20 tipe militer | Google Earth top-down | Bbox + OBB | Terbuka via ScienceDB | Sedang — fine-grained tapi militer & tetap top-down |
| Military Aircraft Detection (Kaggle) | 22.177 citra, 54rb+ bbox, 43 tipe | **Campuran** — banyak ground-level/airshow | Bbox VOC/YOLO | Langsung via Kaggle | **Sedang-tinggi** — sudut pandang lebih dekat ke apron |
| FGVC-Aircraft | 10.200 citra ground-level | Ground-level, 1 objek dominan/citra | Bbox (klasifikasi fine-grained) | Non-commercial, VGG Oxford | Rendah untuk detection multi-instance |
| Roboflow Universe (Apron/Turnaround) | Kecil-menengah, bervariasi per dataset | **Ground-level/CCTV apron**, termasuk ground crew/equipment | Bbox YOLO/COCO | Bervariasi, banyak CC BY 4.0 | **Tinggi** — paling dekat secara visual ke skenario hangar nyata |

## Temuan Kunci

**1. Domain gap fundamental: hampir semua dataset "berkualitas tinggi" adalah citra satelit top-down.** RarePlanes, DOTA, xView, iSAID, DIOR, HRPlanes, MAR20, NWPU — semuanya memotret dari atas. Tidak ada satelit yang memotret interior hangar. Use case Starlight Hangars (kamera CCTV/ground-level di dalam hangar) secara sudut pandang **berbeda signifikan** dari seluruh keluarga dataset satelit ini, termasuk Airbus yang sedang dipakai. Ini keterbatasan yang perlu diakui secara eksplisit, bukan diabaikan.

**2. Dataset yang paling relevan secara sudut pandang justru bukan yang paling "prestisius" secara akademik.** Roboflow Universe (turnaround/apron datasets) dan Kaggle Military Aircraft Detection (banyak foto ground-level) lebih dekat ke skenario nyata, tapi trade-off-nya kualitas & konsistensi anotasi tidak seterjamin dataset akademik yang sudah divalidasi lewat paper resmi (DOTA, RarePlanes).

**3. RarePlanes paling cocok sebagai referensi konseptual, bukan pengganti wajib.** Atribut per-pesawat (orientasi, wingspan, role) relevan untuk narasi "positioning-aware detection", tapi skalanya (butuh AWS setup, non-commercial license sama seperti Airbus) tidak sebanding manfaat inkremental untuk scope portfolio ini.

**4. DOTA/iSAID unggul di satu hal yang sebenarnya penting untuk collision detection: oriented bounding box & segmentation mask.** Bounding box axis-aligned (yang dipakai sekarang) overestimate area collision untuk pesawat yang parkir miring — relevan dicatat sebagai keterbatasan v1/v2 dan arah pengembangan lanjutan (bukan untuk scope saat ini, tapi layak disebut sebagai known limitation).

**5. FGVC-Aircraft & dataset ground-level murni tidak cocok untuk multi-instance detection** karena didesain untuk klasifikasi 1 objek dominan per citra, bukan mendeteksi banyak pesawat dalam satu scene.

## Keputusan

**Tetap pakai dataset Airbus sebagai basis training utama.** Alasannya bukan karena ini dataset "terbaik" secara absolut, tapi karena untuk scope portfolio (bukan riset akademik atau produk produksi), trade-off ukuran-manageable + akses-tanpa-approval + representasi domain top-down yang cukup untuk membuktikan kemampuan spatial reasoning (posisi, jarak, orientasi kasar antar objek) sudah memadai untuk tujuan yang ditetapkan di breakdown project.

**Keterbatasan yang diakui secara eksplisit (didokumentasikan, bukan disembunyikan):**
- Domain gap: model dilatih di citra satelit top-down, sedangkan deployment nyata Starlight Hangars kemungkinan besar pakai kamera ground-level/CCTV di dalam hangar. Model saat ini **tidak divalidasi** untuk sudut pandang tersebut.
- Bounding box axis-aligned bukan representasi geometris paling presisi untuk pesawat yang parkir miring — relevan untuk akurasi collision-check di kasus ekstrem.

**Tindak lanjut yang dipertimbangkan (di luar scope v1-v3 saat ini, dicatat sebagai future work):**
1. Validasi tambahan di 1-2 dataset ground-level/apron dari Roboflow Universe sebagai *secondary evaluation set* — untuk mengukur seberapa besar domain gap tersebut secara empiris, bukan cuma diasumsikan.
2. Eksplorasi migrasi ke oriented bounding box (format DOTA) sebagai peningkatan presisi geometri untuk collision detection.

Dataset yang secara eksplisit **tidak** dipertimbangkan lebih lanjut: xView, DIOR, NWPU VHR-10 — effort integrasi (akun terpisah, ukuran besar, granularitas kelas terlalu general) tidak sebanding manfaat untuk use case spesifik ini.
