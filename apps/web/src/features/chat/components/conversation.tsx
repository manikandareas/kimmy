import { Fragment, useEffect, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowDown } from "lucide-react";
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
import { useRunCommand } from "../hooks/use-run-command";
import { useChatStream } from "../hooks/use-chat-stream";
import {
  useMessageDraft,
  type PendingMessage,
} from "../hooks/use-message-draft";
import { MessageComposer } from "./message-composer";
import { AssistantAnswer } from "./assistant-answer";
import { SourceDialog } from "./source-dialog";
import { RunControls } from "./run-controls";

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
  const [revealing, setRevealing] = useState(false);
  const [revealEpoch, setRevealEpoch] = useState(0);
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
  const cancel = useRunCommand(threadId, active, "cancel");
  const scrollEnd = () => {
    viewport.current?.scrollTo({
      top: viewport.current.scrollHeight,
      behavior: "smooth",
    });
  };
  useEffect(() => {
    const element = viewport.current;
    const content = element?.firstElementChild;
    if (!element || !content) return;
    const observer = new ResizeObserver(() => {
      if (bottom.current) element.scrollTop = element.scrollHeight;
    });
    observer.observe(content);
    return () => observer.disconnect();
  }, []);
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
              if (message.role !== "user") return null;
              const next = state.messages[index + 1];
              const answer = next?.role === "assistant" ? next : undefined;
              const activity = state.activities?.find(
                (a) => a.message_id === message.id,
              );
              const run = active?.message_id === message.id ? active : null;
              return (
                <Fragment key={message.id}>
                  <article
                    data-message-id={message.id}
                    aria-label="Pesan Anda"
                    className="mb-7 ml-auto w-fit max-w-[88%] rounded-2xl bg-neutral-100 px-4 py-3 text-sm leading-7 whitespace-pre-wrap break-words"
                  >
                    {message.content}
                  </article>
                  {(answer ||
                    run ||
                    activity?.text ||
                    activity?.status === "failed" ||
                    activity?.tools?.length) && (
                    <AssistantAnswer
                      onRevealing={
                        index >= state.messages.length - 2
                          ? setRevealing
                          : undefined
                      }
                      revealEpoch={revealEpoch}
                      message={answer}
                      activity={activity}
                      run={run}
                      onSource={setCitation}
                    />
                  )}
                </Fragment>
              );
            })}
            {state?.latest_run && (
              <RunControls threadId={threadId} run={state.latest_run} />
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
          onStop={
            active
              ? () => cancel.mutate()
              : revealing
                ? () => setRevealEpoch((value) => value + 1)
                : undefined
          }
          stopping={cancel.isPending}
          provider={draft.pending?.provider ?? draft.provider}
          onProviderChange={draft.setProvider}
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
