# Kimmy

Asisten operasional armada. Implementasi saat ini mencakup **KM-001: fondasi repository dan boot lokal**.

## Sumber spesifikasi

- [KM-001](https://app.notion.com/p/400abdd6187381f48001e675da62dd70)
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
Service saat ini: postgres (pgvector), api, web (React/Nginx). Migrasi, worker,
seed, SOP, dan deploy Dokploy diimplementasikan pada tiket berikutnya.
Ekstensi vector dan schema domain belum dibuat pada KM-001.

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
Tujuh tabel armada, seed 12 kendaraan/dua depot/60 hari, serta metrik adalah KM-002.

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
