# Kimmy

Asisten operasional armada. Implementasi saat ini mencakup **KM-001: fondasi repository dan boot lokal** serta
**KM-002: skema, seed, dan metrik armada**.

## Sumber spesifikasi

- [KM-001](https://app.notion.com/p/400abdd6187381f48001e675da62dd70)
- [KM-002](https://app.notion.com/p/400abdd6187381a29c7adf973887d56e)
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
`make dev` menjalankan hanya PostgreSQL di Docker, lalu API (Uvicorn reload) dan
web (Vite HMR) sebagai proses CLI lokal. Ctrl+C menghentikan kedua proses lokal;
PostgreSQL tetap tersedia sampai `make down`. Jika salah satu proses keluar,
proses lainnya ikut dihentikan.
Swagger API langsung: http://localhost:9000/docs.
PostgreSQL lokal: localhost:54329, database/user `kimmy`. Port lokal hanya terikat ke loopback.
`make logs` membaca log Docker; log API/web tampil di terminal `make dev`.
`make down` menghentikan infra tanpa menghapus volume.
Untuk preview seluruh stack Docker secara eksplisit, gunakan `make docker-dev`
dan buka http://localhost:8080. Jalankan `make down` sebelum berganti mode.

`compose.yaml` adalah dasar deployment, `compose.local.yaml` menambahkan port lokal.
Service saat ini: postgres (pgvector), api, web (React/Nginx). Migrasi dan seed
armada tersedia melalui perintah eksplisit di bawah. Worker, SOP, ekstensi vector,
dan deploy Dokploy diimplementasikan pada tiket berikutnya.

## Development dan quality gates

```sh
make api-types  # Ekspor OpenAPI offline dan generate src/types/api.generated.ts
make check     # Ruff, format, mypy strict, ESLint, TypeScript, Prettier
make build     # Build React dan kedua image Docker
```

`make format` memperbaiki format. Untuk terminal terpisah, jalankan
`make infra-up`, lalu `make dev-api` dan `make dev-web` di terminal masing-masing.
Launcher API membaca .env dan menyusun koneksi lokal dari POSTGRES_PASSWORD;
KIMMY_DATABASE_URL dapat diberikan sebagai override. Environment KIMMY_* dari .env
hanya diteruskan ke API, bukan proses Vite.
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
kontrak ini untuk domain armada berikutnya; belum ada endpoint armada pada KM-001.
Tujuh tabel armada, seed 12 kendaraan/dua depot/60 hari, serta metrik tersedia
melalui service dan CLI KM-002. Endpoint/tool armada mengikuti tiket berikutnya.

Tidak ada dependency testing, eval, atau Playwright. Verifikasi menggunakan static
checks, build, HTTP langsung, dan walkthrough browser. Belum ada panggilan provider,
chat, memory, RAG atau bukti deployment produksi pada tahap fondasi ini.

## Verifikasi KM-001 — 21 Oktober 2026

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

## Armada — KM-002

```sh
make infra-up
make migrate       # Alembic upgrade head; aman diulang
make seed          # hanya jika seluruh tabel armada kosong
make fleet-report  # laporan KM-001 untuk seluruh periode seed
make fleet-report ARGS='--unit KM-002 --start 2026-08-22T00:00:00Z --end 2026-10-21T00:00:00Z'
```

Migrasi menggunakan `apps/api/alembic.ini` dan tersedia dalam image API. Untuk
runtime Docker, gunakan `docker compose run --rm api /app/.venv/bin/alembic upgrade head`
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
