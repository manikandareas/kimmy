# Kimmy

Asisten operasional armada. Implementasi saat ini mencakup **fondasi repository dan boot lokal**,
**skema, seed, dan metrik armada**, serta **chat persisten,
admission run, dan queue worker**, serta **agent LangChain dengan provider
OpenAI/OpenRouter dan checkpoint PostgreSQL**.

## Sumber spesifikasi

- [Fondasi repository dan boot lokal](https://app.notion.com/p/400abdd6187381f48001e675da62dd70)
- [Data operasional armada dan metrik](https://app.notion.com/p/400abdd6187381a29c7adf973887d56e)
- [Chat persisten dan queue worker](https://app.notion.com/p/400abdd6187381cd88a1fae5d6c37d06)
- [Agent, provider, dan checkpoint](https://app.notion.com/p/400abdd6187381bfa087e80fc84d6355)
- [Architecture & Code](https://app.notion.com/p/400abdd61873812e9a69f25160d1a33d)
- [Database Contract](https://app.notion.com/p/400abdd6187381e1968dd6232f7c0e14)

## Boot lokal

Prasyarat: Docker Compose v2; untuk development host, Python 3.12/3.13, uv, Node 22.12+ dan pnpm 10.28.2.

```sh
cp .env.example .env
# Ganti POSTGRES_PASSWORD dengan password acak URL-safe.
make install
make dev
```

Buka http://localhost:5173. API readiness: http://localhost:5173/api/health/ready.
`make dev` menjalankan hanya PostgreSQL di Docker, menerapkan migrasi, lalu API
(Uvicorn reload), worker, dan web (Vite HMR) sebagai proses CLI lokal.
Ctrl+C menghentikan ketiga proses lokal;
PostgreSQL tetap tersedia sampai `make down`. Jika salah satu proses keluar,
proses lainnya ikut dihentikan.
Swagger API langsung: http://localhost:9000/docs.
PostgreSQL lokal: localhost:54329, database/user `kimmy`. Port lokal hanya terikat ke loopback.
`make logs` membaca log Docker; log API/web tampil di terminal `make dev`.
`make down` menghentikan infra tanpa menghapus volume.
Untuk preview seluruh stack Docker secara eksplisit, gunakan `make docker-dev`
dan buka http://localhost:8080. Jalankan `make down` sebelum berganti mode.

`compose.yaml` adalah dasar deployment, `compose.local.yaml` menambahkan port lokal.
Service saat ini: postgres (pgvector), migrate (one-shot), api, worker, dan web
(React/Nginx). API/worker Docker menunggu migrate berhasil; seed armada tetap
eksplisit. SOP, ekstensi vector, dan deploy Dokploy mengikuti tiket berikutnya.

## Development dan quality gates

```sh
make api-types  # Ekspor OpenAPI offline dan generate src/types/api.generated.ts
make check     # Ruff, format, mypy strict, ESLint, TypeScript, Prettier
make build     # Build React dan kedua image Docker
```

`make format` memperbaiki format. Untuk terminal terpisah, jalankan
`make infra-up`, `make migrate`, lalu `make dev-api`, `make dev-worker`, dan
`make dev-web` di terminal masing-masing. Restart worker setelah mengubah kode
worker; hanya API/web yang memakai reload otomatis.
Launcher API membaca .env dan menyusun koneksi lokal dari POSTGRES_PASSWORD;
KIMMY_DATABASE_URL dapat diberikan sebagai override. Environment KIMMY_*,
OPENAI_API_KEY, dan OPENROUTER_API_KEY dari .env diteruskan ke backend/worker,
bukan proses Vite.
Environment divalidasi ketika aplikasi boot. Secret tidak diteruskan ke build frontend.

## Batas arsitektur

Backend memakai package `kimmy`; engine dibuka/ditutup melalui lifespan FastAPI.
Koneksi memakai UTC, connect timeout 5 detik, statement timeout 5 detik.
`/api/health/live` memeriksa proses, `/api/health/ready` memeriksa DB dan UTC,
`/api/me` menunjukkan identitas demo dari konfigurasi server. Header/payload browser
bukan sumber identitas. Demo ini single-tenant, bukan sistem login produksi.

Frontend: `app` mengomposisikan UI; shared berada di `components`, `lib`, `types`.
ESLint melarang import balik ke app dan import silang feature, termasuk relative imports.
Module feature dibuat ketika tanggung jawabnya diimplementasikan. TanStack Query
menyimpan status server; tipe HTTP berasal dari OpenAPI.

`FleetId` adalah tipe string desimal positif sampai batas bigint PostgreSQL.
Tidak ada konversi menjadi JavaScript number. Export OpenAPI menyertakan komponen
kontrak ini untuk domain armada; endpoint armada belum tersedia.
Tujuh tabel armada, seed 12 kendaraan/dua depot/60 hari, serta metrik tersedia
melalui service dan CLI. Endpoint/tool armada mengikuti tiket berikutnya.

Tidak ada dependency testing, eval, atau Playwright. Verifikasi menggunakan static
checks, build, HTTP langsung, dan walkthrough browser. Chat persisten kini tersedia
melalui API bersama agent/provider. UI chat, tools armada, memory, RAG, dan deployment produksi mengikuti
tiket masing-masing.

## Verifikasi fondasi — 21 Oktober 2026

- `make check`: Ruff/format, mypy strict (8 modul), ESLint, TypeScript, dan Prettier lulus.
- React production build dan image API/web berhasil; ketiga service Compose healthy.
- Walkthrough browser desktop 1280×577 dan mobile 390×844: halaman tampil,
  status siap, tombol periksa ulang bekerja; screenshot lokal di
  `/tmp/kimmy-km001-desktop.png` dan `/tmp/kimmy-km001-mobile.png` (artefak sementara).
- Readiness melalui Nginx dan port API 18000 mengembalikan 200. PostgreSQL timezone UTC.
- Header/query identitas palsu tetap menghasilkan `demo-user` dari konfigurasi server.
- Database dihentikan sementara: readiness 503 dengan error JSON, liveness 200,
  UI menampilkan gangguan. Setelah database dinyalakan, periksa ulang kembali siap.
- FleetId `9007199254740993` dipertahankan sebagai string; input number,
  overflow bigint, nol, negatif, dan desimal ditolak.
- Probe ESLint melalui stdin membuktikan relative import shared → app ditolak.
- Verifikasi awal memakai port API lokal 18000. Port development kini 9000 sesuai permintaan pengguna.

Belum ada commit/push atau deployment Dokploy. Bukti ini mencakup fondasi lokal,
bukan acceptance fitur chat/agent pada tiket berikutnya.

## Development lokal — pembaruan

`make dev` telah diverifikasi dengan hanya service postgres berjalan di Docker.
API host dan proxy Vite mengembalikan readiness 200. Penghentian launcher dengan
SIGINT menutup proses API/web. Docker tetap hanya untuk infra dalam alur development;
Dockerfile dipakai untuk build/preview deployment.

## Armada

```sh
make infra-up
make migrate       # Alembic upgrade head; aman diulang
make seed          # hanya jika seluruh tabel armada kosong
make fleet-report  # laporan KM-001 untuk seluruh periode seed
make fleet-report ARGS='--unit KM-002 --start 2026-08-22T00:00:00Z --end 2026-10-21T00:00:00Z'
```

Migrasi menggunakan `apps/api/alembic.ini` dan tersedia dalam image API. Untuk
runtime Docker, gunakan `docker compose run --rm migrate`
dan `docker compose run --rm api /app/.venv/bin/python -m kimmy.cli seed`.
Migrasi/seed tidak dijalankan otomatis saat API boot. Jangan menghapus volume untuk
mengulang seed: penolakan pada database terisi adalah perilaku yang diharapkan.

Seed tetap menggunakan periode **[22 Agustus 2026 00:00 UTC, 21 Oktober 2026
00:00 UTC)**. Data tidak bergeser mengikuti tanggal eksekusi. Depot MKS (Makassar)
dan PRE (Parepare) memakai zona `Asia/Makassar`. Unit **KM-001** pindah dari MKS
ke PRE pada **21 September 2026 00:00 UTC / 08:00 WITA**. Depot unit kini PRE;
trip, fuel, dan operation sebelum perpindahan tetap memiliki snapshot MKS.
Plat `SIM-001`–`SIM-012` adalah identitas fiktif, bukan registrasi nyata.

Seed berjalan dalam satu transaksi dengan lock tujuh tabel untuk mencegah dua
seed menulis bersamaan. Semua relasi memakai identity hasil INSERT RETURNING;
ID tidak diasumsikan mulai dari satu. Kegagalan membatalkan semua record (sequence
PostgreSQL dapat tetap maju). Jika satu tabel sudah terisi, seed keluar nonzero
sebelum menulis. Tidak ada upsert, import, rekonsiliasi, atau penghapusan data.

Pembacaan berada di `fleet/repository.py`, komposisi laporan di `fleet/service.py`,
dan kalkulasi murni di `fleet/metrics.py`. CLI memakai transaksi read-only dengan
snapshot repeatable-read. Tidak ada endpoint atau UI armada baru pada tiket ini.
ID dalam JSON adalah string desimal; nilai Decimal juga diserialisasi sebagai
string agar presisi terjaga. Periode input wajib timezone-aware dan start < end.

- Full-to-full menjumlahkan liter setelah baseline sampai boundary akhir, termasuk
  partial/unknown dan meter invalid di tengah. Reset memutus interval yang masuk.
  Hasil gabungan memakai total liter / total jarak, bukan rata-rata sederhana rasio.
- Filter depot diterapkan setelah pembentukan interval; semua record interval harus
  memiliki depot yang sama dengan filter. Belanja tetap mencakup seluruh pengisian
  berdasarkan occurred_at, termasuk pengisian yang tidak eligible untuk estimasi.
- `coverage` menjelaskan flag boundary, reset, interval tidak eligible, sesi parsial,
  dan data yang tidak tersedia. Partial/unknown bukan alasan membuang liter interval.
- Jam operasi hanya menjumlahkan engine-on pada sesi complete yang tertutup dan
  seluruhnya masuk periode. Nilai kosong tetap null; nilai nol nyata tetap nol.
  Sesi dipilih berdasarkan started_at; sesi lintas batas tidak diprorata.
- Downtime menggabungkan interval overlap per kendaraan dan memotongnya ke periode
  serta waktu observasi. WO pending tidak dianggap sebagai downtime.
- Filter `--depot` hanya berlaku untuk trip/fuel/operation. Downtime, breakdown,
  dan WO pada laporan tetap per unit; atribusi depot historis tidak tersedia.
  `current_vehicle_depot` adalah depot kini. Status teknis berdasarkan snapshot WO
  kini dan interval breakdown aktif; ini bukan rekonstruksi riwayat status WO.

### Walkthrough manual dan hasil — 21 Oktober 2026

1. Jalankan migrasi dan periksa schema PostgreSQL. Hasil: tujuh tabel armada,
   69 kolom, empat index eksplisit selain PK/UNIQUE. Perbandingan katalog kolom,
   constraint, dan index dengan DDL Notion di schema sementara identik; Alembic
   metadata comparison juga tidak menemukan drift. Sesi database UTC.
2. Seed pertama menghasilkan 2 depot, 12 kendaraan, 716 trip, 713 fuel entry,
   714 operation session, 5 WO, dan 3 breakdown. Seed kedua ditolak; hash seluruh
   record sebelum/sesudah sama. Probe kegagalan di tengah seed membatalkan seluruh
   insert. Dua seed bersamaan menghasilkan satu sukses dan satu penolakan.
3. Probe pada schema sementara memakai identity mulai `9007199254740993`:
   relasi tetap benar dan ID JSON tetap string utuh. Schema probe sudah dihapus;
   data lokal utama tidak diganti oleh probe.
4. KM-001: 60 trip, 360 jam engine-on, 29 interval full-to-full, **20 L/100 km**,
   dan belanja **Rp29.900.000**. Contoh tiga hari pertama: baseline 100.000 km,
   partial 40 L, lalu full 60 L pada 100.500 km → 20 L/100 km. Belanja tiga hari
   tetap Rp1.500.000 karena termasuk 50 L pada baseline.
5. Lihat ID depot dari query berikut, lalu jalankan laporan dengan masing-masing
   `--depot ID`. MKS/PRE masing-masing memiliki 30 trip dan 14 interval eligible.
   Satu interval lintas depot hanya masuk laporan tanpa filter depot. Belanja MKS
   Rp14.900.000 dan PRE Rp15.000.000. Jangan mengasumsikan ID depot selalu 1/2.
6. KM-001 memiliki pengisian 3 September 2026 09:00 UTC yang baru dicatat 30 jam
   kemudian. Pengisian tetap masuk belanja tanggal kejadian.
7. KM-002 mencakup unknown, meter kosong/invalid, reset full sah dan reset partial,
   sesi partial/none, serta breakdown terbuka. Jam lengkap: 342 jam; pengamatan
   partial 3 jam ditampilkan terpisah. Downtime dalam periode: 24 jam. KM-003
   berstatus maintenance; KM-004 maintenance_pending; KM-007 memiliki dua breakdown
   overlap yang menghasilkan total **48 jam**, bukan 71 jam. KM-012 memiliki trip
   in-progress dengan jarak null dan sesi terbuka yang tidak masuk total lengkap.
8. Probe batas menghitung semua liter bermeter invalid, memutus reset, menolak
   interval lintas filter depot/periode, menjaga null versus nol, dan menggabungkan
   downtime per unit. Muatan tidak melebihi kapasitas; WO/breakdown mengacu unit
   yang sama; trip tidak tumpang tindih dengan interval breakdown.
9. `make check` lulus (Ruff, format, mypy, ESLint, TypeScript, Prettier), dan
   `make build` lulus (React production serta image API/web). Verifikasi memakai
   command/SQL dan probe sementara; tidak menambah dependency testing/eval/Playwright.

```sh
docker compose -f compose.yaml -f compose.local.yaml exec -T postgres \
  psql -U kimmy -d kimmy -c 'SELECT id, code, name FROM depots ORDER BY code;'
make fleet-report ARGS='--unit KM-001 --depot ID_DEPOT'
```

Verifikasi ini mencakup fondasi data dan metrik lokal. Chat, agent/tools, memory,
RAG, dan deployment Dokploy mengikuti tiket masing-masing.

## Chat persisten

Empat tabel aplikasi `chat_threads`, `chat_messages`, `chat_runs`, dan `chat_events`
berada pada database yang sama dengan armada dan tabel milik Procrastinate. ID
chat memakai UUID; cursor event bigint dikirim sebagai string desimal. Setiap
thread terikat identitas server. Payload yang mencoba mengirim `user_id` ditolak.

`POST` pesan menerima `request_key` (1–128 karakter alfanumerik, `_`, `-`) dan
`content` (1–20.000 karakter, tidak boleh kosong/whitespace). Scope key adalah
thread milik pengguna. Payload yang sama persis mengembalikan run yang sama,
termasuk setelah terminal/restart; perubahan whitespace juga dianggap perubahan
payload. Key sama dengan content berbeda menghasilkan `409 REQUEST_KEY_CONFLICT`.
Pesan baru saat thread memiliki run queued/running menghasilkan `409 THREAD_BUSY`.
Pemeriksaan replay dilakukan sebelum pemeriksaan busy.

Pesan, run, event awal, dan job Procrastinate di-commit dalam satu transaksi
SQLAlchemy/psycopg. Procrastinate memakai koneksi transaksi yang sama; kegagalan
job INSERT membatalkan semua penulisan. Lock baris thread menserialkan admission,
claim, dan event; unique partial index juga membatasi satu run aktif per thread.
Urutan event mengikuti commit, bukan sequence PostgreSQL yang dapat memiliki gap.

Snapshot memakai transaksi repeatable-read, sehingga transcript/status dan
`through_seq` merujuk kondisi yang sama. History mengambil maksimal 100 pesan
terbaru, ditampilkan dari lama ke baru; `before_seq` mengambil halaman sebelumnya.
`latest_run` mengikuti urutan pesan, bukan waktu awal transaksi. Event diberi
nomor per thread; identitas deduplikasi adalah `(thread_id, seq)` dan message ID.

| Method | Path (prefix `/api/chat`) | Hasil |
| --- | --- | --- |
| POST | `/threads` | 201, thread baru; body `{ "title": "Percakapan" }` opsional memakai `{}` |
| GET | `/threads?limit=50&offset=0` | Daftar thread terbaru dan `next_offset` |
| POST | `/threads/{id}/messages` | 202, `{ "run": ..., "replayed": false/true }` |
| GET | `/threads/{id}/snapshot?limit=100` | Transcript, active/latest run, through_seq, before_seq |
| GET | `/threads/{id}/runs/{run_id}` | Status run tersimpan |
| GET | `/threads/{id}/events?after_seq=0&limit=100` | Halaman event; lanjut dengan next_after_seq |
| GET | `/threads/{id}/stream?after_seq=0` | SSE replay/live dari ledger |

SSE memakai `id` sebagai sequence; `Last-Event-ID` mengungguli query `after_seq`
ketika reconnect. Gunakan `through_seq` snapshot untuk subscription awal. Cursor
melampaui ledger ditolak dengan `409 CURSOR_AHEAD`; cursor invalid menghasilkan
422. Heartbeat dikirim setiap sekitar 15 detik. Pembacaan memakai transaksi
pendek tanpa memegang koneksi selama menunggu. Subscription tidak membuat run,
job, atau panggilan provider. Nginx menonaktifkan buffering SSE.

Worker Procrastinate mengklaim queued run satu kali lalu menjalankan agent LangChain.
Jawaban final, pointer checkpoint, event pesan, dan status completed di-commit dalam
satu transaksi. Job delivery Procrastinate dapat berstatus succeeded sementara run
aplikasi failed: pekerjaan telah ditangani dan kegagalannya disimpan. Pending job
tetap tersimpan ketika worker belum berjalan. Recovery setelah worker crash saat
running, lease/ownership lanjutan, dan cancel/retry tetap pada KM-012. Restart worker
di antara dua run membuktikan persistensi konteks, bukan recovery run yang terputus.

Procrastinate dipin ke 3.10.0. Migrasi 0002 menyertakan snapshot SQL upstream dan
lisensi MIT agar upgrade dependency tidak mengubah migrasi historis. Migrasi
ulang merupakan no-op. Downgrade 0002 ditolak untuk menjaga data chat/queue;
rollback versi database membutuhkan backup. Upgrade Procrastinate berikutnya
harus membawa migrasi upstream yang sesuai.

### Konfigurasi model

Root `.env` memakai `OPENAI_API_KEY` dan `OPENROUTER_API_KEY`; keduanya disimpan
sebagai SecretStr dan hanya diteruskan ke backend/worker. Konfigurasi yang
tersedia untuk integrasi agent:

```dotenv
KIMMY_CHAT_PROVIDER=openai
KIMMY_OPENAI_CHAT_MODEL=gpt-6-luna
KIMMY_OPENROUTER_CHAT_MODEL=deepseek/deepseek-v4.1-flash-1017
```

Nama Luna pada [katalog resmi OpenAI](https://developers.openai.com/api/docs/models)
adalah `gpt-6-luna`, bukan `gpt-6.1-luna`. Model OpenRouter mengikuti permintaan
pengguna. Kedua provider telah diverifikasi pada walkthrough KM-004 di bawah.

### Walkthrough manual dan hasil — 21 Oktober 2026

Verifikasi HTTP/SQL dijalankan dengan API dan worker sebagai proses terpisah,
menggunakan database sementara. Tidak ada framework testing/eval/Playwright
atau dependency baru untuk pengujian.

1. Migrasi database kosong hingga 0002 berhasil; pengulangan no-op dan Alembic
   metadata comparison tidak menemukan drift. Migrasi database lokal utama
   menambahkan chat/queue tanpa mengubah tabel/data armada.
2. 24 POST identik bersamaan menghasilkan tepat satu message, satu run, dan satu
   delivery. Replay memiliki run ID yang sama. Payload berbeda ditolak; pesan
   baru pada thread aktif ditolak. Pemalsuan identitas tidak mengubah pemilik.
3. Trigger sementara memaksa INSERT job PostgreSQL gagal. Respons 500 diikuti
   snapshot kosong, cursor 0, tanpa run/event/job. Setelah trigger dilepas,
   request key yang sama dapat dikirim kembali dan berhasil.
4. API dihentikan dan dijalankan ulang sebelum worker mulai. Snapshot, status,
   cursor, dan replay request identik. SSE Last-Event-ID=1 melanjutkan dari event
   2; membuka/menutup subscription tidak mengubah data atau menambah job.
5. Worker terpisah memproses job setelah seluruh subscription ditutup:
   queued → running → failed dengan AGENT_NOT_CONFIGURED. Tidak ada pesan asisten.
   Duplikasi delivery untuk run terminal tidak menambah event atau mengklaim ulang.
6. Empat pesan menghasilkan event 1–16 berurutan. Pagination history dan event
   lengkap tanpa overlap; cursor invalid/ahead ditolak. Akses thread pengguna
   lain ditolak pada snapshot, run, events, stream, dan admission.
7. `make check` dan `make build` lulus; tipe frontend dihasilkan ulang dari OpenAPI.
8. Boot Compose berhasil: migrate selesai sebelum API/worker, API dan web healthy,
   worker memproses job. Snapshot dan replay SSE melalui Nginx port 8080 berhasil.
   Pemeriksaan environment/build memastikan kedua API key hanya mencapai backend
   dan tidak terdapat dalam bundle frontend. Tidak ada panggilan provider.
9. Urutan latest_run diverifikasi tetap mengikuti sequence pesan walaupun waktu
   transaksi run terakhir dibuat lebih lama dalam database probe. Database probe
   dihapus setelah walkthrough; satu thread bukti Docker tetap ada di database lokal.
10. API development port 9000 dan proxy Vite port 5173 yang sedang berjalan
    berhasil membaca kembali transcript dari walkthrough Docker pada database sama.

Contoh walkthrough lewat Swagger di `http://localhost:9000/docs`: buat thread,
kirim `{ "request_key": "demo-1", "content": "Periksa armada" }`, kirim ulang,
lalu buka snapshot. Untuk melihat queued sebelum worker tersedia, jalankan hanya
`make dev-api`; mulai `make dev-worker` setelah pesan diterima. Saat worker sudah
berjalan dan provider terkonfigurasi, status completed beserta pesan asisten
adalah hasil yang diharapkan. Pertanyaan armada akan menjelaskan keterbatasan
karena tools analisis baru diimplementasikan pada KM-005.

## Agent dan checkpoint — KM-004

Worker memakai `create_agent` dengan adapter native `ChatOpenAI` atau
`ChatOpenRouter`. Model chat dipilih lewat konfigurasi di atas. `llm.py` juga
menyediakan factory embedding OpenAI terpisah; chat tidak membuat embedding atau
membutuhkan key OpenAI ketika provider chat adalah OpenRouter. Factory embedding
belum melakukan ingestion SOP; itu scope KM-007.

| Environment | Default | Fungsi |
| --- | --- | --- |
| `KIMMY_OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Model embedding tersendiri |
| `KIMMY_EMBEDDING_DIMENSIONS` | `1536` | Dimensi embedding |
| `KIMMY_MODEL_TIMEOUT_SECONDS` | `60` | Timeout request provider |
| `KIMMY_AGENT_TIMEOUT_SECONDS` | `180` | Deadline keseluruhan run |
| `KIMMY_AGENT_MAX_TOOL_CALLS` | `8` | Batas eksekusi tool per run |
| `KIMMY_AGENT_MAX_MODEL_CALLS` | `10` | Batas panggilan model per run |
| `KIMMY_AGENT_MAX_OUTPUT_TOKENS` | `4096` | Batas output per panggilan model |

HTTP client ditutup setelah run. Retry otomatis provider dinonaktifkan; retry
command/recovery berikutnya ditangani KM-012. Timeout SDK OpenRouter dikonversi
ke milidetik. Runtime context berisi user, thread, run, dan source message dari
record server yang sudah divalidasi; model tidak memasok identitas tersebut.

`make migrate` menjalankan Alembic hingga 0003, lalu `AsyncPostgresSaver.setup()`.
Compose memakai command yang sama melalui service migrate. Empat tabel native
LangGraph (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`,
`checkpoint_migrations`) berada dalam database yang sama, dengan sesi UTC dan
lifecycle pool eksplisit. Setup diserialkan melalui advisory lock dan aman diulang.
Lockfile mengikat versi library yang membawa migrasi native; upgrade library
checkpointer harus disertai pemeriksaan migrasi. Alembic tidak mengelola tabel
framework sebagai model domain.

Key checkpoint thread berasal dari UUID thread aplikasi. PK bigint tujuh tabel
armada tetap terpisah dan tidak berubah. Migrasi 0003 hanya menambah
`chat_runs.checkpoint_id` untuk menunjuk checkpoint dari run yang berhasil
dipublikasikan. Pesan baru hanya mengirim input baru dengan ID pesan yang stabil;
history tidak ditambahkan ulang ke checkpoint.

Follow-up bercabang dari checkpoint run completed terakhir. Checkpoint sementara
dari run failed tidak menjadi konteks run berikutnya, termasuk bila kegagalan
terjadi setelah model selesai tetapi sebelum publikasi final. Pesan pengguna yang
gagal tetap terlihat dalam history, tetapi percobaan gagal tidak dimasukkan ke
konteks agent berikutnya. Thread tanpa run berhasil dimulai dari konteks kosong.
Belum ada profil lintas thread atau tool operasional yang didaftarkan.

Event tambahan pada ledger:

| Kind | Payload | Makna |
| --- | --- | --- |
| `agent.text_delta` | `model_message_id`, `text` | Teks sementara per pesan model, dibatch; bukan pesan transcript final |
| `tool.requested` | `tool_call_id`, `name` | Model meminta tool; belum menjamin eksekusinya diizinkan limit |
| `tool.completed` | `tool_call_id`, `name`, `status` | Hasil eksekusi tool tersedia |
| `message.created` | `message` | Pesan final canonical, dengan UUID aplikasi |
| `run.completed` | `run` | Jawaban dan pointer checkpoint sudah tersimpan |

Reasoning dan argumen tool tidak dipublikasikan pada text delta. SSE hanya
membaca event tersimpan. UI nantinya harus mengganti preview dengan pesan final,
bukan menggabungkannya menjadi pesan kedua; pada failed preview bukan jawaban final.
Snapshot menjamin transcript final/status, sementara progress detail tersedia
melalui ledger. Jangan memperlakukan `model_message_id` sebagai UUID pesan aplikasi.

Error publik: `AGENT_NOT_CONFIGURED` (key tidak tersedia), `AGENT_TIMEOUT`
(deadline run), `AGENT_LIMIT_EXCEEDED`, `AGENT_INVALID_RESULT` (jawaban/checkpoint
akhir tidak lengkap), `AGENT_EXECUTION_FAILED` (provider/eksekusi gagal), serta
`WORKER_INTERRUPTED` untuk cancellation proses yang dapat ditangani. Error mentah
provider tidak dikirim ke klien atau dicatat di log aplikasi. Crash/SIGKILL dan
database tidak tersedia saat penyimpanan kegagalan memerlukan recovery KM-012.

### Walkthrough manual dan hasil — 21 Oktober 2026

Verifikasi memakai database PostgreSQL sementara, API/worker sebagai proses
terpisah, HTTP/SSE langsung, panggilan provider nyata, dan probe Python sementara.
Tidak ada dependency testing/eval/Playwright yang ditambahkan.

1. OpenAI `gpt-6-luna` dan OpenRouter `deepseek/deepseek-v4.1-flash-1017`
   menjawab lewat antrean sampai completed. Ledger berisi text delta, pesan final,
   dan run completed dengan sequence berurutan.
2. Kedua provider mengingat kode `MERPATI-4829` pada follow-up setelah worker
   direstart. Thread baru mulai dengan transcript kosong dan menyatakan tidak
   mengetahui kode dari thread lain. Dua run menghasilkan empat pesan, tanpa duplikat.
3. Tool probe sementara dipanggil oleh kedua model native dan menerima identitas
   dari `ToolRuntime[AgentContext]`. Tool probe tidak didaftarkan dalam aplikasi.
   Factory embedding terpisah menghasilkan vektor 1536 dimensi dari OpenAI.
4. Model tidak valid menghasilkan failed; deadline satu detik menghasilkan
   `AGENT_TIMEOUT`. Tidak ada pesan asisten palsu dan thread kembali menerima
   pesan baru. Follow-up setelah keduanya tetap membaca checkpoint berhasil.
5. Subscription SSE ditutup saat run berlangsung; run tetap completed. Restart
   API menghasilkan snapshot identik, replay SSE melanjutkan setelah cursor, dan
   request key yang sama mengembalikan run lama tanpa event/jawaban tambahan.
6. Header/query user palsu tidak mengganti identitas server; payload `user_id`
   ditolak. Probe loop terkontrol membuktikan batas model/tool menghentikan run
   dengan `AGENT_LIMIT_EXCEEDED`, tanpa jawaban final atau tool berlebih.
7. Trigger PostgreSQL sementara menolak event completed: transaksi membatalkan
   pesan asisten dan pointer checkpoint, lalu run menjadi failed. Run pertama
   berikutnya memakai konteks kosong meskipun checkpoint gagal masih tersimpan.
8. Migrasi database kosong dan pengulangannya berhasil; Alembic metadata comparison
   tidak menemukan drift dan sesi checkpoint/database memakai UTC.
9. `make check`, `make build`, dan migrasi melalui image Docker lulus. Export
   OpenAPI tetap menghasilkan tipe frontend yang sama. Development lokal di-restart;
   API 9000 dan proxy Vite 5173 siap. Satu thread bukti lokal mencapai completed
   dan menyatakan tools armada belum tersedia. Database probe sudah dihapus.

Belum ada commit, push, atau deployment Dokploy. UI chat, tools analisis,
memory/RAG, dan recovery worker crash tetap mengikuti tiket masing-masing.
