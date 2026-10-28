---
tags: [kimmy, peta-belajar]
---
# Belajar Kimmy: agent dan streaming

Mulai dengan satu pertanyaan: **bagaimana pertanyaan pengguna berubah menjadi jawaban yang tetap dapat diikuti setelah browser terputus?**

Vault ini menghubungkan konsep dengan kode lokal. Bacaan utama berupa Markdown dengan wikilink dan diagram Mermaid bawaan Obsidian. HTML pendamping menyediakan kuis di browser, tanpa plugin tambahan.

## Rute belajar
1. [[lessons/0001-loop-agent|Loop agent]] — pisahkan keputusan model dan pekerjaan service.
2. [[lessons/0002-dua-stream|Dua stream dan ledger]] — ikuti delta dari model ke UI.
3. [[lessons/0003-reconnect|Reconnect]] — pahami snapshot, cursor, dan deduplikasi.
4. [[lessons/0004-run-checkpoint|Run dan checkpoint]] — pisahkan recovery UI dan pekerjaan.

Luangkan 5–10 menit per pelajaran. Jawab latihan sebelum membuka umpan balik. Besok, gambar ulang alur pelajaran 2 dari ingatan; tiga hari kemudian jelaskan perbedaan reconnect dan retry menggunakan contoh sendiri. Jadwal ini saran latihan, bukan penilaian kemampuan.

## Rencana perbaikan

- [[plans/Pertahankan Draf saat Run Gagal]] — mempertahankan respons sementara saat eksekusi gagal. Status: diimplementasikan lokal; validasi deployment belum dilakukan.

## Referensi
- [[reference/Alur Chat dan Worker|Cara kerja chat, worker Procrastinate, dan streaming]] — panduan alur lengkap dari kirim pesan sampai jawaban final.
- [[reference/Glosarium]]
- [[reference/Peta Kode]]
- [[MISSION]]
- [[RESOURCES]]
- [[NOTES]]

## Membuka vault
Di Obsidian pilih **Open folder as vault**, lalu pilih direktori `.teachme` di repo Kimmy. Folder bertitik mungkin tersembunyi pada dialog macOS; tekan **Cmd+Shift+G** lalu masukkan path lengkap folder. Mulai dari catatan `Home`.

Untuk kuis, buka file HTML pada folder `lessons` dengan browser. Skrip kuis berjalan lokal; Markdown tetap bisa dipakai sepenuhnya di Obsidian.

## Melanjutkan sesi
Kirim: “Lanjut teach Kimmy pelajaran 1; ini jawaban latihanku: …”. Learning record baru dibuat setelah ada bukti pemahaman. Belum ada klaim kamu sudah menguasai materi ini.
