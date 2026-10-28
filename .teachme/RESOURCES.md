# Resources: Kimmy agent dan streaming

## Knowledge
- [LangChain Agents](https://docs.langchain.com/oss/python/langchain/agents): sumber resmi loop model/tool dan `create_agent`; pelajaran 1.
- [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence): sumber resmi checkpoint dan cakupan state; pelajaran 4. MemoryService Kimmy adalah implementasi aplikasi tersendiri, jangan disamakan otomatis dengan LangGraph Store.
- [MDN: Using server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events): format SSE, named event, `id`, dan koneksi satu arah; pelajaran 2–3.
- [[reference/Peta Kode]]: sumber utama perilaku spesifik Kimmy, diperiksa langsung 2026-10-28. Dokumentasi framework tidak menggantikan kode aplikasi.

## Wisdom (Communities)
- [Forum LangChain](https://forum.langchain.com/): tempat mendiskusikan tradeoff framework dengan praktisi. Belum dievaluasi kualitas setiap jawaban; cocok untuk meminta umpan balik atas reproduksi minimal, bukan otoritas kontrak Kimmy.

## Gaps
Belum ada hasil latihan pengguna, pengujian live provider, atau walkthrough recovery dalam sesi ini. Dokumentasi online bisa lebih baru dari versi terpasang; cocokkan dengan `apps/api/pyproject.toml` dan lockfile sebelum mengubah API.
