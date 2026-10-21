import { useQuery } from "@tanstack/react-query";
import { apiGet, apiRequest } from "@/lib/api-client";
import type { components } from "@/types/api.generated";
export const memoryKey = ["memory", "profile"] as const;
export type Memory = components["schemas"]["MemoryView"];
export const useMemories = (enabled: boolean) =>
  useQuery({
    queryKey: memoryKey,
    queryFn: ({ signal }) =>
      apiGet<components["schemas"]["MemoryProfile"]>("/memories", signal),
    enabled,
    staleTime: 0,
  });
export const updateMemory = (memory: Memory, content: string) =>
  apiRequest<components["schemas"]["MemoryReceipt"]>(`/memories/${memory.id}`, {
    method: "PATCH",
    body: JSON.stringify({ content, expected_revision: memory.revision }),
  });
export const forgetMemory = (memory: Memory) =>
  apiRequest<components["schemas"]["MemoryReceipt"]>(
    `/memories/${memory.id}/forget`,
    {
      method: "POST",
      body: JSON.stringify({ expected_revision: memory.revision }),
    },
  );
