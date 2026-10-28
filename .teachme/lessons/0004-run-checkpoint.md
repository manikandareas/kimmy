---
tags: [kimmy, belajar, agent, streaming]
status: belum-dilatih
---
# Run, checkpoint, dan worker yang berhak

Target: membedakan recovery koneksi dari recovery pekerjaan.

Saat POST pesan diterima, `ChatService.admit` membuat pesan, run, event awal, dan job Procrastinate dalam satu transaksi database. `enqueue_run` meminjam koneksi psycopg dari session SQLAlchemy yang sama. Dengan demikian penulisan job mengikuti commit/rollback transaksi penerimaan pesan.

`request_key` memungkinkan pengulangan permintaan yang sama menghasilkan admission replay. Payload berbeda yang berkonflik ditolak; adanya run aktif juga dapat menghasilkan `THREAD_BUSY`.

Worker pada `jobs/tasks.py` memanggil `claim`, memperoleh token kepemilikan, menjalankan executor, dan mengirim heartbeat setiap 5 detik. Claim/heartbeat memberi lease 30 detik. `require_owner` memeriksa token, status running, dan masa berlaku lease. Worker lama yang kehilangan hak tidak boleh menerbitkan progress atau completion baru melalui jalur service tersebut.

Checkpoint menyimpan state graph; ledger menyimpan event aplikasi yang bisa dibaca UI. `stream_answer` menggunakan checkpoint parent eksplisit, `FencedCheckpoints`, dan `durability="sync"`. Selesai streaming saja belum cukup: kode memeriksa teks final, tool call tersisa, finish reason tertentu, checkpoint selesai, dan citation sebelum publikasi.

| Mekanisme | Yang dilanjutkan | Tempat membaca |
|---|---|---|
| Reconnect SSE | Pengamatan UI | `use-chat-stream.ts` |
| Resume checkpoint | Eksekusi graph dari state tersimpan | `chat/execution.py` |
| Retry eksplisit | Run diantrekan ulang dari checkpoint publik terakhir | `ChatService.command` |

Pada resume, input `astream` adalah `None`; pada turn baru, inputnya HumanMessage. Retry eksplisit mengosongkan `resume_checkpoint_id`. Detail kebijakan recovery otomatis ada pada `ChatService.recover`; jangan menyimpulkan semua kegagalan otomatis diulang atau semua tool pasti exactly-once.

**Latihan:** browser offline tetapi worker masih sehat. Apakah perlu retry run? Jelaskan juga mengapa checkpoint tidak menggantikan ledger.

<details><summary>Umpan balik</summary>Tidak perlu retry hanya karena browser offline; lakukan rekonsiliasi UI. Checkpoint mendukung kelanjutan graph, sedangkan ledger menyediakan urutan event publik bagi UI.</details>

Sumber utama: [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence). Ulangi [[0002-dua-stream]] besok tanpa melihat diagram.

[[Home]] · [[reference/Glosarium]] · [Latihan interaktif](0004-run-checkpoint.html)

Tanyakan kepada agent bagian yang belum jelas. Setelah latihan, kirim jawaban dengan kata-katamu sendiri.
