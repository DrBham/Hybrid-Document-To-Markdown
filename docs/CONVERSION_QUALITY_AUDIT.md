# Audit kualitas konversi — 10 November 2026

Audit ini memisahkan **perilaku yang direproduksi**, **risiko dari pembacaan kode**, dan **kemampuan yang belum diuji**. Semua contoh menggunakan data sintetis. Ini bukan klaim bahwa semua format sudah lossless atau aman terhadap semua dokumen tidak tepercaya.

## 1. Arsitektur saat ini

```text
python -m document_converter
  → PySide6 MainWindow
  → ConversionWorker / QThread
  → BatchConverter (satu ekstensi, hasil independen per file)
  → ConverterRouter → validate_file
  → EmbeddedMediaDocumentConverter
      → MarkItDownConverter → MarkItDown.convert_local
      → DocumentImageExtractor → gambar sementara → Base64
  → ConversionResult → preview / clipboard / MarkdownExporter
```

`src/document_converter/core/models.py` menyimpan path, format, dan Markdown. Belum ada warning, lokasi sumber, statistik ekstraksi, pilihan konversi, atau daftar aset. Kegagalan dicatat sebagai string per file oleh batch; belum ada sistem logging terstruktur. Ekspor dan pengisian preview masih dilakukan di thread GUI.

`core/markdown_builder.py` dan `converters/txt_converter.py` adalah jalur pembelajaran/alternatif, bukan jalur router bawaan. Heuristik Setext/list/kode pada TXT lama tidak boleh dianggap sebagai perilaku produksi. Validasi dipanggil di router dan adapter; duplikasi kecil ini bukan prioritas dibanding kehilangan data.

**Keputusan:** pertahankan adapter, router, layanan batch, GUI, dan Base64. Tambahkan opsi/peringatan secara kompatibel sebelum mempertimbangkan model dokumen lengkap. `Document/Section/Table/SourceLocation` dapat diperkenalkan hanya pada parser yang membutuhkannya; jangan memaksa JSON, PDF, dan workbook ke satu struktur yang membuang semantik.

## 2. Inventaris converter dan dependensi

Semua ekstensi berikut saat ini memakai `converters/markitdown_converter.py` melalui dekorator media yang sama. Inventaris diverifikasi dari source package yang terpasang, bukan dugaan dari nama dependency.

| Format | Jalur pembacaan terpasang | Status bukti |
|---|---|---|
| TXT | MarkItDown PlainTextConverter, charset-normalizer | Smoke test + probe whitespace |
| JSON | Jalur plain text pada contoh audit | Angka, key, null, dan nesting contoh tetap utuh; belum fenced |
| XML | Jalur teks pada contoh audit | Namespace, atribut, CDATA, komentar contoh tetap utuh; bukan parser XML semantik khusus |
| CSV | `csv.reader` dalam MarkItDown | String dan pipe terjaga; delimiter/multiline bermasalah |
| HTML/HTM | BeautifulSoup `html.parser` → custom markdownify | Heading dasar lulus; probe preformatted dan URL relatif |
| DOCX | Mammoth → HTML → markdownify | Teks dasar + gambar PNG nyata lulus |
| PPTX | python-pptx | Judul dasar lulus; source upstream sudah menangani urutan slide, koordinat shape, grup, notes, chart tertentu |
| XLSX | pandas `read_excel` / openpyxl → HTML → Markdown | Nilai/formula probe menunjukkan kehilangan informasi |
| PDF | pdfplumber + pdfminer.six fallback; pypdfium2 untuk halaman PNG | Teks dasar dan raster halaman lulus; layout kompleks belum dinilai |

Media OOXML dibaca melalui `zipfile`; Pillow digunakan saat menyimpan raster PDF. `requirements.in` menyatakan PySide6, MarkItDown extras, pytest. Beberapa package yang diimpor langsung oleh proyek/test masih bergantung pada instalasi transitif, misalnya pypdfium2, Pillow, python-docx pada tes. Perlu uji instalasi bersih sebelum rilis. Tidak ada OCR/model training/cloud client yang dikonfigurasi di jalur aplikasi. Ini tidak menyatakan bahwa lingkungan Python pengguna bebas paket lama yang tidak dipakai.

## 3. Baseline dan reproduksi

Lingkungan audit: Windows, Python 3.13, MarkItDown 0.1.9, PySide6 6.12. Tes menggunakan Qt offscreen, bukan pemeriksaan visual desktop.

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe tools\audit_conversion_quality.py
```

- Baseline sebelum perubahan: **80 passed in 5.85s**.
- Setelah checkpoint whitespace: **92 passed in 5.74s**.
- Tes media baru dijalankan terhadap source `HEAD` lama di memori: **8 gagal, 8 lulus**. Ini membuktikan regresi terdeteksi tanpa mengganti file kerja.
- Durasi di atas adalah durasi tes satu kali, bukan benchmark konversi.
- Suite awal mencakup semua ekstensi, validasi, batch, ekspor, GUI, ekstraksi media. Banyak tes format hanya memeriksa substring. Belum ada corpus kompleks/golden, benchmark memori, atau skor fidelity menyeluruh.

### Contoh hasil sebelum checkpoint

| Fixture | Sumber | Hasil teramati | Penilaian |
|---|---|---|---|
| TXT | `"line with hard break  \nnext\n\n\n    code\t  \n\n"` | `"line with hard break\nnext\n\n    code\n"` | Spasi akhir, tab akhir, dan blank line berubah |
| XLSX | Sel string `00123`, `1.2300`, `9007199254740993`; formula `=1+2` | `123`, `1.230000e+00`, `9.007199e+15`, `NaN` | Identitas/presisi/formula tidak setia; workbook sintetis belum memiliki cached result |
| CSV koma | `00123`, `1.2300`, `9007199254740993`, `a\|b` sebagai isi sel | Nol awal dan digit utuh; pipe di-escape | Perilaku baik yang harus dipertahankan |
| CSV multiline | Satu sel berisi `"line1\nline2"` | `line1 line2` | Batas baris hilang |
| CSV semicolon | Header `id;note` | Satu kolom `id;note` | Tidak mendeteksi delimiter `;` |
| HTML | `<pre>` dengan trailing spaces/3 newline; gambar `images/chart.png` | Spasi/newline berubah; referensi tetap relatif tanpa aset | Belum portable setelah dipindahkan |
| JSON/XML | Nesting, angka literal, namespace, atribut, CDATA | Teks contoh utuh, tanpa code fence | Jangan mengklaim konten hilang pada contoh ini; masalah representasi/rendering masih ada |

## 4. Temuan berprioritas

P1 = kehilangan data nyata atau risiko sumber daya/ekspor utama; P2 = struktur, portabilitas, dan kemampuan observasi; P3 = perapian setelah kontrak fidelity jelas. Risiko kode belum sama dengan eksploitasi yang direproduksi.

| ID / tingkat | Modul terdampak dan bukti | Perbaikan yang disarankan / hasil yang diharapkan | Risiko regresi |
|---|---|---|---|
| Q01 / P1 | `converters/markitdown_converter.py`; normalisasi global upstream `_markitdown.py` melakukan `line.rstrip()` dan membatasi blank line. Probe TXT/HTML mengonfirmasi perubahan. Dekorator proyek juga memakai `rstrip()` pada seluruh hasil. | Hapus pemangkasan di dekorator (selesai); jalur preserve TXT/structured data dan preformatted terpisah berikutnya. Teks bermakna tidak berubah. | Rendah untuk dekorator; sedang untuk perubahan routing/encoding |
| Q02 / P1 | Adapter XLSX upstream `read_excel` menginferensi tipe; probe di atas kehilangan nol awal, digit dan formula. | Parser workbook berbasis sel; simpan tipe/raw value/formula/cache/number format secara terpisah. Jangan menghitung ulang atau menyebut cache pasti terbaru. | Sedang–tinggi: bentuk tabel dan tipe berubah |
| Q03 / P1 | `embedded_media/extractor.py`: semua PDF dirender `scale=2`; ZIP `archive.read()` tanpa anggaran dekompresi; `converter.py` menampung seluruh Base64 dalam memori. Batas validator hanya input 100 MiB. | Batas jumlah entry, ukuran terurai, page/pixel/output; fail/warn eksplisit. Mode original-image dan full-page opsional setelah kontrak kompatibilitas disepakati. | Sedang: dokumen besar yang dulu diterima bisa ditolak |
| Q04 / P1 | `services/markdown_exporter.py`: overwrite memakai `write_text` langsung. Kegagalan tulis berpotensi merusak file lama; belum ada fault injection. | Temporary sibling + replace atomik, cleanup, pertahankan no-overwrite eksklusif; uji disk/write/replace failure. | Sedang: permission, filesystem, overwrite race |
| Q05 / P2 | `embedded_media/extractor.py`: urutan nama ZIP bukan relationship sumber; semua media yang cocok diambil, tanpa caption/anchor. PDF berupa raster baru, bukan byte gambar asli. | Resolusi relationship DOCX/slide/sheet; source location dan deduplikasi berbasis konten; laporkan visual tidak didukung. | Tinggi untuk inline placement; jangan hapus appendix sebelum ada regresi |
| Q06 / P2 | Adapter CSV upstream: probe newline sel hilang, `;` satu kolom. Sel berkoma sudah string dan pipe aman. | Dialect/encoding eksplisit + deteksi terbatas; representasi multiline reversible atau raw fallback. Pertahankan angka sebagai string. | Sedang: delimiter ambigu, escaping dan multiline |
| Q07 / P2 | Adapter JSON/XML saat ini teks tanpa fence. XML dapat dianggap markup oleh renderer. | Fence dengan panjang aman terhadap backtick sumber, encoding eksplisit; pertahankan sumber tanpa parse/re-serialize. Parser XML semantik kelak harus menolak external entity. | Rendah–sedang: bentuk output berubah, escape fence wajib benar |
| Q08 / P2 | `core/models.py` tanpa warning/provenance/options. Ekstraksi media gagal menggagalkan hasil teks juga. Mammoth messages tidak diteruskan adapter. | Tambah field default yang kompatibel; bedakan sukses, sukses dengan peringatan, gagal. Jangan membuat hitungan palsu. | Sedang: kebijakan partial success harus jelas |
| Q09 / P2 | Adapter HTML + extractor hanya PDF/OOXML: link/aset relatif tidak disalin; probe HTML mengonfirmasi. | Resolve terhadap lokasi sumber; aset lokal terbatas root yang diizinkan; mode Base64/assets; hindari network otomatis. | Sedang: traversal, URL aktif, kompatibilitas viewer |
| Q10 / P2 | `gui/main_window.py`: worker sudah di QThread, tetapi tidak ada cancellation; preview/copy/export memuat seluruh string pada GUI. Close ditolak selama worker hidup. | Cancellation kooperatif antar-file/page dan preview dibatasi tanpa memotong data ekspor; benchmark sebelum ubah UI. | Sedang–tinggi: lifecycle worker; jangan terminate thread paksa |
| Q11 / P2 | `embedded_media/extractor.py`: bitmap/page ditutup hanya setelah save berhasil, document di finally. | `try/finally` per resource dan fault injection render/save. | Rendah; lifetime bitmap/PIL perlu diperhatikan |
| Q12 / P2 | `tests/test_multiformat_integration.py`: substring bukan bukti struktur; belum ada corpus kompleks. PDF upstream memiliki heuristik tabel/nomor; PPTX sudah punya notes/chart. | Golden fixtures berdasarkan output yang ditinjau terhadap sumber; uji order, merged cells, footnotes, chart, malformed/empty/Unicode. Jangan menganggap kemampuan upstream belum ada. | Rendah untuk tes; baseline manual perlu waktu |
| Q13 / P3 | README sebelumnya menyatakan jaminan byte gambar terlalu luas; dependency langsung/transitif belum dipisah penuh. | Jelaskan batas OOXML vs raster PDF; uji instalasi bersih, inventory runtime, lisensi final. | Rendah; tidak ada dependency baru pada checkpoint ini |

## 5. Kelemahan lintas-format dan batas keamanan

- Normalisasi global tidak mengetahui apakah teks adalah log, source code, JSON, prose, atau tabel. Hindari satu fungsi cleanup agresif untuk semua format.
- String Markdown tunggal menghilangkan kesempatan membawa warnings dan hubungan aset. Tambahkan metadata bertahap sebelum model dokumen menyeluruh.
- Keberhasilan konversi tidak sama dengan kesetiaan sumber. Heading, merged cells, footnotes DOCX, reading order PDF, dan diagram/chart kompleks belum divalidasi terhadap corpus.
- Allowlist ekstensi, batas input, sanitasi nama output media, temporary directory, dan no-overwrite eksklusif sudah berguna. Itu belum membatasi ZIP bomb, raster raksasa, atau semua perilaku parser pihak ketiga.
- HTML diparse tanpa menjalankan JavaScript dan upstream membuang script/style. Referensi SVG/URL/HTML hasil tetap memerlukan kebijakan jika kelak dirender aktif. Belum dilakukan pentest, fuzzing, network interception, atau pengujian macro/external entity menyeluruh.
- Tidak ditemukan model/OCR/cloud aktif di kode aplikasi. API `convert_local` dipakai; jaminan offline pada semua dokumen tetap memerlukan tes yang memblokir network pada fase hardening.

## 6. Roadmap bertahap

Penomoran Q1–Q6 membedakan pekerjaan kualitas ini dari milestone produk A–F. Setiap checkpoint diakhiri tes, perbandingan sumber/hasil, dokumentasi, dan daftar batas. Fase rilis F menunggu gerbang kualitas; bukan membatalkan fitur E.

| Fase | Checkpoint terbatas, berurutan | Gerbang selesai |
|---|---|---|
| Q1 — Baseline & audit | 1A inventaris + baseline; 1B probe fidelity + ranking; 1C koreksi whitespace dekorator + tes + dokumen | Selesai pada audit ini; bukan seluruh peningkatan engine |
| Q2 — Infrastruktur kualitas | 2A kontrak opsi/peringatan kompatibel; 2B ekspor atomik; 2C anggaran resource + cleanup; 2D serializer/fence/table helpers dan validator terbatas | Fault injection lulus; caller lama tetap berjalan; warning jujur |
| Q3 — Parser per format | 3A preserve TXT/JSON/XML; 3B CSV dialect/multiline; 3C XLSX raw/formula/cache; 3D DOCX semantic order/tabel/footnotes; 3E PPTX notes/chart/group; 3F HTML/pre/URL; 3G PDF reading order/tabel/scan detection | Setiap format punya fixture sumber, oracle, dan before/after sendiri |
| Q4 — Aset & opsi lanjutan | 4A relationship + lokasi gambar; 4B Base64/assets directory dan dedup; 4C PDF original images + full-page mode; 4D evaluasi profil setelah kontrak stabil | Aset valid dan portable; Base64 lama tetap tersedia; OCR tetap di luar scope saat ini |
| Q5 — Evaluasi & optimasi | 5A corpus/golden lengkap dan metrik; 5B waktu/memori + stress/fault tests; 5C cancellation/preview + security/offline regression | Angka diukur pada corpus dan perangkat tercatat, tidak mengarang akurasi |
| Q6 — Dokumentasi & rilis | 6A matriks kemampuan/batas + changelog; 6B clean install/dependency/license inventory; 6C startup/package smoke, renderer compatibility, installer | Release artifact teruji, dokumentasi sesuai perilaku nyata |

Urutan dapat mengangkat batas resource atau ekspor atomik sebelum fitur baru karena dampaknya lintas-format. Tes ditambahkan pada setiap fase; Q5 memperluas evaluasi, bukan menunda QA sampai akhir.

### Detail checkpoint Phase 1

| Checkpoint | Lingkup dan artefak | Validasi / status |
|---|---|---|
| 1A | Baca repository, README, entry point, dependencies, parser terpasang, worker, exporter, media, tes | Baseline 80 lulus; inventaris di bagian 1–2. Selesai |
| 1B | Probe sintetis TXT/CSV/JSON/XML/HTML/XLSX; bedakan reproduksi dan risiko statis | Script `tools/audit_conversion_quality.py`, contoh bagian 3, Q01–Q13. Selesai; bukan corpus semua layout |
| 1C | Hentikan normalisasi tambahan oleh dekorator; uji exact text dengan/tanpa media dan round-trip gambar | 12 parameterized cases baru; 8 mendeteksi bug lama; full suite 92 lulus. Selesai |

### Laporan checkpoint 1C

- **Perubahan/file:** `src/document_converter/embedded_media/converter.py` mempertahankan hasil base converter persis dan hanya menambah pemisah sebelum appendix gambar. `tests/test_embedded_media_converter.py` menguji whitespace, teks kosong, media/tanpa media, dan byte gambar DOCX. README, audit ini, script probe, dan CHANGELOG mendokumentasikan hasil.
- **Mekanisme:** `rstrip()` menghapus semua whitespace paling belakang. Menghilangkannya menjaga hard break Markdown, tab, dan blank lines. Appendix dipisahkan oleh paling sedikit satu baris kosong tanpa menghapus karakter sumber.
- **Before/after:** hasil converter `"hard break  \n"` sebelumnya menjadi `"hard break\n"` tanpa media; sekarang tetap `"hard break  \n"`. `"text\n\n\n"` sebelumnya menjadi `"text\n"`; sekarang tetap utuh. Dengan media, seluruh string sumber tetap prefix sebelum separator/appendix.
- **Tes:** baseline 80; regresi pada kode lama 8 gagal; suite setelah patch 92 lulus termasuk alur worker/export GUI offscreen, semua ekstensi dasar, Base64.
- **Batas:** normalisasi upstream masih mengubah TXT/preformatted sebelum dekorator menerimanya. Perbaikan ini bukan klaim TXT lossless end-to-end. Tidak mengubah mode PDF, GUI, dependency, atau jalur konverter.
- **Berikutnya:** Q2A, kontrak `ConversionOptions`/warning dengan default kompatibel dan tes caller lama; lanjut Q2B ekspor atomik. Q3A mengatasi whitespace dari parser secara menyeluruh.

## 7. Metrik dan risiko pelaksanaan

Belum ada angka akurasi corpus atau benchmark RAM. Definisi berikut merupakan rencana pengukuran; gunakan N/A bila denominator nol dan jangan merata-ratakan format tanpa jumlah sampel.

| Metrik | Perhitungan / oracle |
|---|---|
| Text preservation | Karakter yang cocok dalam longest common subsequence teks hasil ekstraksi vs teks referensi berurutan / jumlah karakter referensi. Hanya normalisasi newline jika kontrak fixture mengizinkan; laporkan insertion terpisah agar tambahan palsu tidak tersembunyi. Exact equality wajib untuk mode preserve. |
| Table cell fidelity | Sel yang isi, tipe yang diwajibkan, dan koordinatnya tepat / jumlah sel referensi; laporkan sel/row/column hilang atau tambahan secara terpisah. |
| Heading accuracy | Heading dengan teks, level, dan posisi tepat / jumlah heading referensi; precision terpisah memakai jumlah heading keluaran. |
| Asset success | Referensi aset yang resolve/decode dan cocok dengan byte referensi / jumlah aset yang diharapkan; PDF raster dinilai terpisah karena bukan byte original. |
| Markdown validation | Fixture yang lulus aturan parser/validator yang disebutkan / fixture yang diperiksa; GFM tables dipisahkan dari CommonMark. |
| Error frequency | Konversi gagal tak terduga / input valid; penolakan dokumen malformed yang diharapkan dilaporkan terpisah. |
| Duration / memory | Ukur `perf_counter` per dokumen di subprocess, laporkan ukuran/page/cell, hardware, versi, median/p95 dan peak RSS termasuk native memory. `tracemalloc` saja tidak cukup untuk Qt/PDF. |

Risiko terbesar adalah perubahan bentuk output (snapshot konsumen), ambiguitas encoding/delimiter, inferensi reading order PDF, formula cache tidak tersedia/usang, aset vektor tidak didukung, penggunaan native memory, serta variasi viewer Base64. Uji contoh kecil sebelum dokumen besar. Pertahankan default yang kompatibel sampai pilihan baru terdokumentasi. Jangan menambah library sebelum kemampuan dependency sekarang dan kewajiban distribusinya diperiksa.

## 8. Kekuatan yang dipertahankan

- Router/adapter memungkinkan koreksi per format tanpa menulis ulang GUI.
- Outcome per file menjaga keberhasilan batch saat file lain gagal.
- QThread sudah memisahkan konversi dari event loop GUI; progress indeterminate tidak mengarang persentase.
- Export `.md`, UTF-8, exclusive create, dan nama tabrakan GUI sudah punya tes.
- Base64 menyediakan satu file output; temporary media dikelola context manager.
- Fixture sintetis dan dependency injection memudahkan regresi tanpa dokumen pribadi.
- Tidak ada penambahan cloud, training, atau model berat pada audit ini.
