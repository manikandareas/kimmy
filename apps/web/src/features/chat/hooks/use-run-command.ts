import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";
import { toast } from "sonner";
import { apiRequest, displayError } from "@/lib/api-client";
import { chatKeys, type Run } from "../api";

export function useRunCommand(
  threadId: string,
  run: Run | null | undefined,
  action: "cancel" | "retry",
) {
  const client = useQueryClient();
  const key = useRef<{ scope: string; value: string } | null>(null);
  return useMutation({
    mutationFn: () => {
      if (!run) throw new Error("No run to update");
      const scope = `${run.id}:${run.attempts}:${action}`;
      if (key.current?.scope !== scope)
        key.current = { scope, value: crypto.randomUUID() };
      return apiRequest<Run>(
        `/chat/threads/${threadId}/runs/${run.id}/${action}`,
        {
          method: "POST",
          body: JSON.stringify({
            request_key: key.current.value,
            expected_attempt: run.attempts,
          }),
        },
      );
    },
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: chatKeys.snapshot(threadId) });
    },
    onError: (error) => {
      toast.error(displayError(error));
      void client.invalidateQueries({ queryKey: chatKeys.snapshot(threadId) });
    },
  });
}
