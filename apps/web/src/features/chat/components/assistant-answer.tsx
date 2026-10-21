import { useEffect } from "react";
import { Copy, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import type { Activity, Citation, Message, Run } from "../api";
import { useSmoothText } from "../hooks/use-smooth-text";
import { MessageContent } from "./message-content";
import { ToolActivity } from "./tool-activity";

export function AssistantAnswer({
  message,
  activity,
  run,
  onSource,
  onRevealing,
  revealEpoch,
}: {
  onRevealing?: (revealing: boolean) => void;
  revealEpoch?: number;
  message?: Message;
  activity?: Activity;
  run?: Run | null;
  onSource: (citation: Citation) => void;
}) {
  const text = message?.content ?? activity?.text ?? "";
  const visible = useSmoothText(text, !message, revealEpoch);
  useEffect(() => {
    onRevealing?.(visible !== text);
  }, [visible, text, onRevealing]);
  useEffect(() => () => onRevealing?.(false), [onRevealing]);
  return (
    <article
      aria-label={message ? "Jawaban Kimmy" : "Jawaban sedang diproses"}
      data-message-id={message?.id}
      className="mb-10 min-w-0 text-sm leading-7"
    >
      <ToolActivity tools={activity?.tools ?? []} />
      {visible ? (
        <MessageContent
          content={visible}
          citations={message?.citations}
          onSource={onSource}
        />
      ) : (
        run && (
          <p
            role="status"
            className="flex items-center gap-2 text-muted-foreground"
          >
            <Loader2 className="size-3.5 animate-spin" />
            {run.status === "queued"
              ? "Menunggu giliran…"
              : "Kimmy sedang memproses…"}
          </p>
        )
      )}
      {message && visible === text && (
        <Button
          variant="ghost"
          size="icon-sm"
          className="mt-3 text-muted-foreground"
          aria-label="Salin jawaban"
          onClick={() =>
            void navigator.clipboard
              .writeText(text)
              .then(() => toast.success("Jawaban disalin"))
              .catch(() => toast.error("Jawaban belum dapat disalin."))
          }
        >
          <Copy className="size-3.5" />
        </Button>
      )}
    </article>
  );
}
