import { useInfiniteQuery } from "@tanstack/react-query";
import { apiGet, apiRequest } from "@/lib/api-client";
import type { components } from "@/types/api.generated";
export type Snapshot = components["schemas"]["Snapshot"];
export type Message = components["schemas"]["MessageView"];
export type Run = components["schemas"]["RunView"];
export type Activity = components["schemas"]["RunActivity"];
export type ToolActivity = components["schemas"]["ToolActivity"];
export type Citation = components["schemas"]["Citation"];
export type ChatEvent = components["schemas"]["EventView"];
export const chatKeys = {
  threads: ["chat", "threads"] as const,
  snapshot: (id: string) => ["chat", "snapshot", id] as const,
};
export function useThreads() {
  return useInfiniteQuery({
    queryKey: chatKeys.threads,
    initialPageParam: 0,
    queryFn: ({ pageParam, signal }) =>
      apiGet<components["schemas"]["ThreadPage"]>(
        `/chat/threads?offset=${pageParam}`,
        signal,
      ),
    getNextPageParam: (page) => page.next_offset ?? undefined,
  });
}
export const createThread = (title: string) =>
  apiRequest<components["schemas"]["ThreadView"]>("/chat/threads", {
    method: "POST",
    body: JSON.stringify({ title }),
  });
export const getSnapshot = (
  id: string,
  signal?: AbortSignal,
  before?: string,
) =>
  apiGet<Snapshot>(
    `/chat/threads/${id}/snapshot${before ? `?before_seq=${before}` : ""}`,
    signal,
  );
export const sendMessage = (
  id: string,
  request: components["schemas"]["SendMessage"],
) =>
  apiRequest<components["schemas"]["Admission"]>(
    `/chat/threads/${id}/messages`,
    { method: "POST", body: JSON.stringify(request) },
  );
export const getSource = (id: string, signal?: AbortSignal) =>
  apiGet<components["schemas"]["SourceChunk"]>(
    `/knowledge/sources/${id}`,
    signal,
  );
