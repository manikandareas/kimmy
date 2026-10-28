---
tags: [kimmy, plan, chat, recovery]
status: diimplementasikan-lokal
---
# Pertahankan draf saat run gagal

## Masalah

Teks streaming dapat terlihat lalu menghilang ketika run gagal. Frontend mengosongkan `activity.text` saat run menjadi terminal; backend hanya merekonstruksi teks aktivitas untuk run aktif. Karena validasi akhir gagal, tidak ada pesan assistant final yang menggantikan teks sementara.

Pada insiden yang dibahas, embedding OpenAI mengembalikan 429 dan run berakhir dengan `AGENT_INVALID_RESULT`. Kredit habis merupakan dugaan pengguna untuk penyebab 429. Alasan spesifik penolakan hasil akhir belum terbukti dari log yang tersedia.

## Hasil yang diinginkan

Teks yang sudah diterima tetap terlihat sebagai **draf belum selesai**, termasuk setelah refresh atau reconnect. Draf tidak dianggap sebagai jawaban final yang valid.

Contoh label:

> Jawaban belum selesai dan belum lolos validasi. Sebagian informasi mungkin tidak lengkap.

## Rencana implementasi

### 1. Pertahankan draf pada jalur event live

Di `apps/web/src/features/chat/events.ts`, jangan kosongkan teks ketika menerima `run.failed`. Hentikan indikator proses. Saat berhasil, pesan final tetap menggantikan teks sementara. Perilaku cancel perlu ditetapkan secara eksplisit sebelum implementasi; perubahan awal difokuskan pada run gagal.

### 2. Rekonstruksi draf melalui snapshot

Di `apps/api/src/kimmy/chat/activity.py`, ubah `project_activity()` agar menyusun teks run gagal dari event `agent.text_delta`, selain run aktif. Gunakan aturan pergantian `model_message_id` dan reset `run.queued` yang konsisten dengan reducer frontend.

Delta yang sudah tersimpan dapat digunakan kembali tanpa tabel baru. Cakupan awal hanya teks yang sudah masuk ledger, bukan buffer yang belum sempat disimpan ketika proses mati.

### 3. Tampilkan status pada respons terkait

Sertakan status run pada proyeksi aktivitas agar setiap respons, termasuk respons lama, dapat diberi label yang benar. Sinkronkan kontrak backend dan tipe frontend.

Perbarui `Conversation` dan `AssistantAnswer` agar draf tetap dirender ketika tidak ada run aktif, pesan final, maupun aktivitas tool. Jangan tampilkan draf sebagai citation terverifikasi atau menyimpannya sebagai pesan assistant final. Pertahankan pemeriksaan validasi sebelum `service.complete()`.

### 4. Pisahkan percobaan retry

Untuk lingkup awal, draf lama diganti ketika retry benar-benar dimulai melalui event `run.queued`. Jangan mencampur teks dua percobaan. Jika percobaan baru gagal, pertahankan draf terbarunya. Menyimpan semua draf per percobaan sebagai riwayat terpisah merupakan pengembangan lain.

### 5. Perjelas alasan validasi gagal

Tambahkan kode alasan internal yang aman pada log `InvalidAgentResult`, misalnya `FINAL_TEXT_EMPTY`, `OUTPUT_TRUNCATED`, dan `INVALID_CITATION`, bersama `run_id`. Hindari mencatat isi prompt, kredensial, atau exception provider mentah. Setiap cabang penolakan harus tetap dapat dibedakan.

## Acceptance dan verifikasi

- Run gagal setelah streaming: draf tetap terlihat dengan label gagal dan tanpa indikator berjalan.
- Refresh, pindah thread lalu kembali, dan reconnect: draf dari ledger muncul kembali dengan status yang konsisten.
- Gagal sebelum ada teks: pesan gagal ditampilkan tanpa bubble kosong.
- Run gagal tanpa tool call: draf tetap dirender.
- Retry: teks antarpercobaan tidak tercampur; delta baru tidak digandakan oleh replay.
- Run berhasil: pesan final menggantikan draf tanpa duplikasi.
- Citation tidak valid tidak ditampilkan sebagai sumber terverifikasi.
- Status cancel ditangani sesuai keputusan implementasi dan tidak mengalami regresi.
- Jalankan `make check`, `make build`, dan walkthrough manual sesuai aturan proyek; jangan menambah dependency testing/eval/Playwright V1.

## Bukti verifikasi lokal

- `make check`: lulus lint, format, dan pemeriksaan tipe backend/frontend.
- Pemeriksaan langsung proyeksi snapshot: draf failed dipertahankan, reset retry diterapkan, completed/cancelled tidak mempertahankan draf.
- Pemeriksaan langsung reducer TypeScript: draf failed dipertahankan, replay dideduplikasi, retry mereset teks, dan pesan final menggantikan draf.
- Build frontend: lulus.
- Belum ada walkthrough browser atau eksekusi provider deployment. Bukti di atas tidak menggantikan acceptance end-to-end.

## Batas lingkup

Perubahan telah diimplementasikan lokal. Pemeriksaan statis dan proyeksi snapshot lulus; walkthrough browser/provider deployment belum dilakukan. Cancel tetap menghapus draf; retry mengganti draf lama. Perbaikan kuota embedding dan kebijakan percobaan ulang pencarian SOP merupakan pekerjaan terpisah. Menaikkan batas tool call tidak mengatasi hilangnya draf atau menjamin validitas jawaban.

[[Home]] · [[reference/Alur Chat dan Worker|Alur chat dan worker]] · [[lessons/0004-run-checkpoint|Run dan checkpoint]]
