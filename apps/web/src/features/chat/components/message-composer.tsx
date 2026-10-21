import { ArrowUp, Loader2, RotateCcw } from "lucide-react";
import { useLayoutEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
export function MessageComposer({
  value,
  onChange,
  onSend,
  busy = false,
  sending = false,
  pending = false,
}: {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  busy?: boolean;
  sending?: boolean;
  pending?: boolean;
}) {
  const input = useRef<HTMLTextAreaElement>(null);
  useLayoutEffect(() => {
    if (input.current) {
      input.current.style.height = "auto";
      input.current.style.height = `${Math.min(input.current.scrollHeight, 176)}px`;
    }
  }, [value]);
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (!busy && !sending && value.trim()) onSend();
      }}
      className="w-full"
    >
      <div className="flex items-end gap-2 rounded-[26px] border border-neutral-200 bg-neutral-50 p-2 pl-5 transition-colors focus-within:border-neutral-400 focus-within:bg-white">
        <Textarea
          ref={input}
          aria-label="Pesan untuk Kimmy"
          placeholder="Tanyakan tentang armada Anda…"
          value={value}
          maxLength={20000}
          readOnly={pending || sending}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            if (
              e.key === "Enter" &&
              !e.shiftKey &&
              !e.nativeEvent.isComposing
            ) {
              e.preventDefault();
              if (!busy && !sending && value.trim()) onSend();
            }
          }}
          rows={1}
          className="min-h-10 resize-none rounded-none border-0 bg-transparent px-0 py-2.5 text-base shadow-none focus-visible:ring-0 md:text-sm"
        />
        <Button
          type="submit"
          size="icon"
          aria-label={
            pending ? "Kirim ulang permintaan yang sama" : "Kirim pesan"
          }
          disabled={busy || sending || !value.trim()}
          className="mb-0.5 size-9 shrink-0 rounded-full shadow-none"
        >
          {sending ? (
            <Loader2 className="size-4 animate-spin" />
          ) : pending ? (
            <RotateCcw className="size-4" />
          ) : (
            <ArrowUp className="size-4" />
          )}
        </Button>
      </div>
    </form>
  );
}
