import { useEffect, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowDown, Copy, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ApiError, displayError, errorMessage } from "@/lib/api-client";
import {
  chatKeys,
  getSnapshot,
  sendMessage,
  type Citation,
  type Snapshot,
} from "../api";
import { useChatStream } from "../hooks/use-chat-stream";
import {
  useMessageDraft,
  type PendingMessage,
} from "../hooks/use-message-draft";
import { MessageComposer } from "./message-composer";
import { MessageContent } from "./message-content";
import { SourceDialog } from "./source-dialog";
import { ToolActivity } from "./tool-activity";

export function Conversation({
  threadId,
  onMemoryChange,
}: {
  threadId: string;
  onMemoryChange: () => void;
}) {
  const client = useQueryClient();
  const query = useChatStream(threadId, onMemoryChange);
  const draft = useMessageDraft(threadId);
  const [citation, setCitation] = useState<Citation | null>(null);
  const [atBottom, setAtBottom] = useState(true);
  const viewport = useRef<HTMLDivElement>(null);
  const initialSubmission = useRef(false);
  const bottom = useRef(true);
  const submit = useMutation({
    mutationFn: (request: PendingMessage) => sendMessage(threadId, request),
    onSuccess: () => {
      draft.acknowledge();
      void client.invalidateQueries({ queryKey: chatKeys.threads });
      void client.invalidateQueries({ queryKey: chatKeys.snapshot(threadId) });
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status < 500) draft.reject();
      toast.error(displayError(error), { id: `send-${threadId}` });
    },
  });
  useEffect(() => {
    if (!initialSubmission.current) {
      initialSubmission.current = true;
      if (draft.pending) submit.mutate(draft.pending);
    }
    // Recover only once per mounted thread; transport failures remain explicit retries.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const state = query.data;
  const active = state?.active_run;
  const progress = state?.activities?.find((a) => a.run_id === active?.id);
  const activeIndex =
    state?.messages.findIndex((m) => m.id === active?.message_id) ?? -1;
  const finalPresent =
    activeIndex >= 0 && state?.messages[activeIndex + 1]?.role === "assistant";
  const scrollEnd = () => {
    viewport.current?.scrollTo({
      top: viewport.current.scrollHeight,
      behavior: "smooth",
    });
  };
  useEffect(() => {
    if (bottom.current && viewport.current)
      viewport.current.scrollTop = viewport.current.scrollHeight;
  }, [state?.messages.length, progress?.text, progress?.tools?.length]);
  useEffect(() => {
    if (state?.latest_run?.status === "failed")
      toast.error(errorMessage(state.latest_run.error_code), {
        id: `run-${state.latest_run.id}`,
        duration: 8000,
      });
  }, [
    state?.latest_run?.id,
    state?.latest_run?.status,
    state?.latest_run?.error_code,
  ]);
  const older = useMutation({
    mutationFn: () =>
      getSnapshot(threadId, undefined, state?.before_seq ?? undefined),
    onSuccess: (page) => {
      const height = viewport.current?.scrollHeight ?? 0;
      const top = viewport.current?.scrollTop ?? 0;
      client.setQueryData<Snapshot>(chatKeys.snapshot(threadId), (current) =>
        current
          ? {
              ...current,
              before_seq: page.before_seq,
              messages: [
                ...page.messages.filter(
                  (m) => !current.messages.some((old) => old.id === m.id),
                ),
                ...current.messages,
              ],
              activities: [
                ...(page.activities ?? []).filter(
                  (a) =>
                    !current.activities?.some((old) => old.run_id === a.run_id),
                ),
                ...(current.activities ?? []),
              ],
            }
          : current,
      );
      requestAnimationFrame(() => {
        if (viewport.current)
          viewport.current.scrollTop =
            top + viewport.current.scrollHeight - height;
      });
    },
    onError: (error) => toast.error(displayError(error)),
  });
  return (
    <>
      <div className="relative min-h-0 flex-1">
        <div
          ref={viewport}
          onScroll={(e) => {
            const el = e.currentTarget;
            bottom.current =
              el.scrollHeight - el.scrollTop - el.clientHeight < 100;
            setAtBottom(bottom.current);
          }}
          className="h-full overflow-y-auto overscroll-contain px-5"
          aria-label="Percakapan"
        >
          <div className="mx-auto max-w-3xl pb-10 pt-8 sm:px-4">
            {query.isPending && (
              <p role="status" className="text-sm text-muted-foreground">
                Memuat percakapan…
              </p>
            )}
            {query.isError && (
              <Button variant="outline" onClick={() => void query.refetch()}>
                Muat ulang percakapan
              </Button>
            )}
            {state?.before_seq && (
              <div className="mb-8 text-center">
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={older.isPending}
                  onClick={() => older.mutate()}
                >
                  Muat pesan sebelumnya
                </Button>
              </div>
            )}
            {state?.messages.length === 0 && (
              <p className="py-20 text-center text-muted-foreground">
                Apa yang ingin Anda ketahui tentang armada?
              </p>
            )}
            {state?.messages.map((message, index) => {
              const activity =
                message.role === "assistant"
                  ? state.activities?.find(
                      (a) => a.message_id === state.messages[index - 1]?.id,
                    )
                  : undefined;
              return (
                <article
                  key={message.id}
                  data-message-id={message.id}
                  aria-label={
                    message.role === "user" ? "Pesan Anda" : "Jawaban Kimmy"
                  }
                  className={
                    message.role === "user"
                      ? "mb-7 ml-auto w-fit max-w-[88%] rounded-2xl bg-neutral-100 px-4 py-3 text-sm leading-7 whitespace-pre-wrap break-words"
                      : "mb-10 min-w-0 text-sm leading-7"
                  }
                >
                  {message.role === "user" ? (
                    message.content
                  ) : (
                    <>
                      <ToolActivity tools={activity?.tools ?? []} />
                      <MessageContent
                        content={message.content}
                        citations={message.citations}
                        onSource={setCitation}
                      />
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        className="mt-3 text-muted-foreground"
                        aria-label="Salin jawaban"
                        onClick={() =>
                          void navigator.clipboard
                            .writeText(message.content)
                            .then(() => toast.success("Jawaban disalin"))
                            .catch(() =>
                              toast.error("Jawaban belum dapat disalin."),
                            )
                        }
                      >
                        <Copy className="size-3.5" />
                      </Button>
                    </>
                  )}
                </article>
              );
            })}
            {active && !finalPresent && (
              <div
                aria-label="Jawaban sedang diproses"
                className="text-sm leading-7"
              >
                <ToolActivity tools={progress?.tools ?? []} />
                {progress?.text ? (
                  <MessageContent content={progress.text} />
                ) : (
                  <p
                    role="status"
                    className="flex items-center gap-2 text-muted-foreground"
                  >
                    <Loader2 className="size-3.5 animate-spin" />
                    {active.status === "queued"
                      ? "Menunggu giliran…"
                      : "Kimmy sedang memproses…"}
                  </p>
                )}
              </div>
            )}
            {!active && state?.latest_run?.status === "failed" && (
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span>Jawaban belum selesai.</span>
                <Button
                  variant="ghost"
                  size="xs"
                  onClick={() =>
                    toast.error(errorMessage(state.latest_run?.error_code))
                  }
                >
                  Lihat keterangan
                </Button>
              </div>
            )}
          </div>
        </div>
        {!atBottom && (
          <Button
            variant="outline"
            size="icon-sm"
            className="absolute bottom-3 left-1/2 rounded-full bg-white"
            aria-label="Ke pesan terbaru"
            onClick={scrollEnd}
          >
            <ArrowDown />
          </Button>
        )}
      </div>
      <div className="mx-auto w-full max-w-3xl px-5 pb-5 pt-2 sm:px-4">
        <MessageComposer
          value={draft.draft}
          onChange={draft.setDraft}
          busy={!state || (!!active && !draft.pending)}
          sending={submit.isPending}
          pending={!!draft.pending}
          onSend={() => {
            bottom.current = true;
            submit.mutate(draft.pending ?? draft.stage(draft.draft.trim()));
          }}
        />
      </div>
      <SourceDialog citation={citation} onClose={() => setCitation(null)} />
    </>
  );
}
