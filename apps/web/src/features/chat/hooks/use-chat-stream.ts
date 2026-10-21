import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { errorMessage } from "@/lib/api-client";
import {
  chatKeys,
  getSnapshot,
  type ChatEvent,
  type Run,
  type Snapshot,
} from "../api";
import { applyEvent, eventKinds } from "../events";

export function useChatStream(threadId: string, onMemoryChange: () => void) {
  const client = useQueryClient();
  const query = useQuery({
    queryKey: chatKeys.snapshot(threadId),
    queryFn: ({ signal }) => getSnapshot(threadId, signal),
    structuralSharing: (previous, incoming) => {
      const old = previous as Snapshot | undefined;
      const next = incoming as Snapshot;
      // A fetch started before a live event must never roll the cache backward.
      if (old && BigInt(old.through_seq) > BigInt(next.through_seq)) return old;
      return next;
    },
    staleTime: Infinity,
    refetchOnWindowFocus: false,
    refetchOnReconnect: (query) => !query.state.data,
  });
  const ready = !!query.data;
  useEffect(() => {
    if (!ready) return;
    let disposed = false;
    let source: EventSource | undefined;
    let retry: ReturnType<typeof setTimeout> | undefined;
    const key = chatKeys.snapshot(threadId);
    const connect = () => {
      const snapshot = client.getQueryData<Snapshot>(key);
      if (!snapshot || disposed) return;
      source = new EventSource(
        `/api/chat/threads/${threadId}/stream?after_seq=${snapshot.through_seq}`,
      );
      source.onopen = () => {
        if (!disposed) {
          toast.dismiss(`connection-${threadId}`);
        }
      };
      const reconnect = () => {
        if (disposed) return;
        source?.close();
        clearTimeout(retry);
        toast.error("Koneksi terputus. Menghubungkan kembali…", {
          id: `connection-${threadId}`,
        });
        retry = setTimeout(() => {
          void client
            .fetchQuery({
              queryKey: key,
              queryFn: ({ signal }) => getSnapshot(threadId, signal),
              staleTime: 0,
            })
            .then(connect)
            .catch(reconnect);
        }, 2000);
      };
      source.onerror = reconnect;
      source.addEventListener("stream.error", reconnect);
      for (const kind of eventKinds)
        source.addEventListener(kind, (message) => {
          if (disposed) return;
          try {
            const event = JSON.parse(
              (message as MessageEvent<string>).data,
            ) as ChatEvent;
            const current = client.getQueryData<Snapshot>(key);
            if (
              event.thread_id !== threadId ||
              !current ||
              BigInt(event.seq) <= BigInt(current.through_seq)
            )
              return;
            client.setQueryData<Snapshot>(key, applyEvent(current, event));
            if (kind === "run.failed")
              toast.error(errorMessage((event.payload.run as Run).error_code), {
                id: `run-${event.run_id}`,
                duration: 8000,
              });
            if (
              kind === "tool.completed" &&
              ["remember_memory", "forget_memory"].includes(
                String(event.payload.name),
              )
            )
              onMemoryChange();
            if (["run.completed", "run.failed", "run.queued"].includes(kind))
              void client.invalidateQueries({ queryKey: chatKeys.threads });
          } catch {
            reconnect();
          }
        });
    };
    // Always reconcile on mount (including returning to a cached thread).
    void client
      .fetchQuery({
        queryKey: key,
        queryFn: ({ signal }) => getSnapshot(threadId, signal),
        staleTime: 0,
      })
      .then(connect)
      .catch(() => {
        if (!disposed) connect();
      });
    return () => {
      disposed = true;
      source?.close();
      clearTimeout(retry);
      toast.dismiss(`connection-${threadId}`);
    };
  }, [client, threadId, ready, onMemoryChange]);
  return query;
}
