# Peta Kode

Snapshot dibaca 2026-10-28. Path relatif terhadap root repo; dari direktori vault root repo ada di `..`. Gunakan editor proyek untuk menavigasi simbol berikut.

| Tujuan | File | Simbol |
|---|---|---|
| Merakit agent | `apps/api/src/kimmy/agent/factory.py` | `build_agent` |
| Instruksi model | `apps/api/src/kimmy/agent/prompt.md` | system prompt |
| Contoh tool | `apps/api/src/kimmy/agent/tools/search_vehicles.py` | `build_tool` |
| Eksekusi dan batching delta | `apps/api/src/kimmy/chat/execution.py` | `stream_answer`, `AgentExecutor.execute` |
| Penerimaan dan lifecycle | `apps/api/src/kimmy/chat/service.py` | `admit`, `progress`, `complete`, `command`, `recover` |
| Job dalam transaksi | `apps/api/src/kimmy/jobs/queue.py` | `enqueue_run` |
| Worker dan heartbeat | `apps/api/src/kimmy/jobs/tasks.py` | `register_tasks` |
| Guard kepemilikan | `apps/api/src/kimmy/chat/ownership.py` | `require_owner` |
| Endpoint SSE | `apps/api/src/kimmy/chat/router.py` | `stream`, `parse_cursor` |
| Pembacaan ledger | `apps/api/src/kimmy/chat/stream.py` | `stream_events` |
| Koneksi dan rekonsiliasi UI | `apps/web/src/features/chat/hooks/use-chat-stream.ts` | `useChatStream` |
| Penerapan event | `apps/web/src/features/chat/events.ts` | `applyEvent` |

## Cara membaca tanpa tersesat
Mulai dari [[../lessons/0002-dua-stream|dua stream]]. Telusuri satu nama event, `agent.text_delta`, dari producer ke consumer. Baru telusuri `run.completed`. Jangan mulai dari seluruh repository sekaligus.

[[Home]] · [[Glosarium]]
