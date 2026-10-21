import { ArrowUp, Loader2, RotateCcw, Square } from "lucide-react";
import { useLayoutEffect, useRef, type RefObject } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ModelSelect, type Provider } from "./model-select";
export function MessageComposer({
  inputRef,
  provider,
  onProviderChange,
  value,
  onChange,
  onSend,
  onStop,
  stopping = false,
  busy = false,
  sending = false,
  pending = false,
}: {
  inputRef?: RefObject<HTMLTextAreaElement | null>;
  provider?: Provider;
  onProviderChange: (provider: Provider) => void;
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  onStop?: () => void;
  stopping?: boolean;
  busy?: boolean;
  sending?: boolean;
  pending?: boolean;
}) {
  const localInput = useRef<HTMLTextAreaElement>(null);
  const input = inputRef ?? localInput;
  useLayoutEffect(() => {
    if (input.current) {
      input.current.style.height = "auto";
      input.current.style.height = `${Math.min(input.current.scrollHeight, 176)}px`;
    }
  }, [value, input]);
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (!busy && !sending && value.trim()) onSend();
      }}
      className="w-full"
    >
      <div className="flex flex-wrap items-end gap-2 rounded-[26px] sm:flex-nowrap border border-neutral-200 bg-neutral-50 p-2 pl-5 transition-colors focus-within:border-neutral-400 focus-within:bg-white">
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
          className="min-h-10 w-full min-w-0 sm:flex-1 resize-none rounded-none border-0 bg-transparent px-0 py-2.5 text-base shadow-none focus-visible:ring-0 md:text-sm"
        />
        <div className="mb-1 ml-auto flex shrink-0 items-center gap-1">
          <ModelSelect
            value={provider}
            onChange={onProviderChange}
            disabled={pending || sending}
          />
          <Button
            type={onStop ? "button" : "submit"}
            onClick={onStop}
            size="icon"
            aria-label={
              onStop
                ? "Hentikan respons"
                : pending
                  ? "Kirim ulang permintaan yang sama"
                  : "Kirim pesan"
            }
            disabled={onStop ? stopping : busy || sending || !value.trim()}
            className="mb-0.5 size-9 shrink-0 rounded-full shadow-none"
          >
            {onStop ? (
              stopping ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Square className="size-3.5 fill-current" />
              )
            ) : sending ? (
              <Loader2 className="size-4 animate-spin" />
            ) : pending ? (
              <RotateCcw className="size-4" />
            ) : (
              <ArrowUp className="size-4" />
            )}
          </Button>
        </div>
      </div>
    </form>
  );
}
