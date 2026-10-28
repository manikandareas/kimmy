---
tags: [kimmy, belajar, agent, streaming]
status: belum-dilatih
---
# Reconnect tanpa menggandakan teks

Target: menjelaskan bagaimana UI melanjutkan pengamatan setelah jaringan putus.

`useChatStream` membaca snapshot, lalu membuka EventSource dengan `after_seq=snapshot.through_seq`. Snapshot merupakan kondisi UI pada batas urutan tertentu; event setelah batas itu melanjutkan kondisi tersebut.

Saat koneksi error, hook menutup EventSource, menunggu 2 detik, mengambil snapshot baru, kemudian membuat koneksi baru. Ini rekonsiliasi eksplisit aplikasi. Secara terpisah, router mendukung header `Last-Event-ID` dan memprioritaskannya atas query `after_seq`; dukungan protokol itu jangan dianggap sebagai satu-satunya jalur reconnect hook ini.

`applyEvent` dan hook mengabaikan event thread lain serta event dengan `seq <= through_seq`. Karena ID urutan dikirim sebagai string desimal, perbandingan memakai `BigInt`, bukan perbandingan alfabet string atau Number yang berpotensi kehilangan presisi. Sequence merupakan urutan per thread.

Contoh: cache sudah melewati `42`; event `41` dan `42` diabaikan, sedangkan `43` dapat diterapkan. Ini mengatasi pengiriman ulang event lama; kode tersebut bukan detektor semua gap urutan.

Ada perlindungan race tambahan: `structuralSharing` menolak snapshot yang `through_seq`-nya lebih tua dari cache. Fetch yang dimulai sebelum event live tidak boleh memundurkan state.

**Latihan:** cache sudah `105`. Snapshot terlambat membawa `103`. Apa yang terjadi? Lalu event `106` datang dua kali; berapa kali teksnya ditambahkan?

<details><summary>Umpan balik</summary>Snapshot lama ditolak. Event 106 pertama diterapkan dan cursor maju; salinan keduanya diabaikan. Mengunduh snapshot tidak menjalankan ulang agent.</details>

Sumber utama: [MDN SSE](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events). Berikutnya [[0004-run-checkpoint]].

[[Home]] · [[reference/Glosarium]] · [Latihan interaktif](0003-reconnect.html)

Tanyakan kepada agent bagian yang belum jelas. Setelah latihan, kirim jawaban dengan kata-katamu sendiri.
