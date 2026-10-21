import { useRef } from "react";
import { StarterSuggestions } from "./starter-suggestions";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { displayError } from "@/lib/api-client";
import { createThread } from "../api";
import { useMessageDraft } from "../hooks/use-message-draft";
import { MessageComposer } from "./message-composer";
export function NewConversation({
  onCreated,
}: {
  onCreated: (id: string) => void;
}) {
  const composer = useRef<HTMLTextAreaElement>(null);
  const draft = useMessageDraft("new");
  const mutation = useMutation({
    mutationFn: async () => {
      const content = draft.draft.trim();
      const thread = await createThread(content.slice(0, 100));
      // Stage before navigation so a refresh/retry retains the exact command.
      localStorage.setItem(
        `kimmy:composer:${thread.id}`,
        JSON.stringify({
          draft: content,
          provider: draft.provider,
          pending: {
            content,
            request_key: crypto.randomUUID(),
            provider: draft.provider,
          },
        }),
      );
      return thread;
    },
    onSuccess: (thread) => {
      draft.acknowledge();
      onCreated(thread.id);
    },
    onError: (error) => toast.error(displayError(error)),
  });
  return (
    <div className="flex min-h-0 flex-1 flex-col items-center justify-center overflow-y-auto px-5 py-8 sm:pb-[10vh]">
      <div className="my-auto w-full max-w-2xl">
        <p className="mb-3 text-sm text-muted-foreground">
          Asisten operasional armada
        </p>
        <h1 className="mb-6 text-3xl font-medium tracking-tight sm:text-4xl">
          Apa yang ingin Anda ketahui?
        </h1>
        <StarterSuggestions
          disabled={mutation.isPending}
          onSelect={(prompt) => {
            draft.setDraft(prompt);
            requestAnimationFrame(() => composer.current?.focus());
          }}
        />
        <MessageComposer
          inputRef={composer}
          provider={draft.pending?.provider ?? draft.provider}
          onProviderChange={draft.setProvider}
          value={draft.draft}
          onChange={draft.setDraft}
          onSend={() => mutation.mutate()}
          sending={mutation.isPending}
        />
      </div>
    </div>
  );
}
