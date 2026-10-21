import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { displayError } from "@/lib/api-client";
import {
  forgetMemory,
  memoryKey,
  updateMemory,
  useMemories,
  type Memory,
} from "../api";
function MemoryItem({
  memory,
  onChanged,
}: {
  memory: Memory;
  onChanged: () => void;
}) {
  const client = useQueryClient();
  const [edit, setEdit] = useState<{
    content: string;
    revision: number;
  } | null>(null);
  const mutation = useMutation({
    mutationFn: (action: "save" | "forget") =>
      action === "forget"
        ? forgetMemory(memory)
        : updateMemory(
            { ...memory, revision: edit!.revision },
            edit!.content.trim(),
          ),
    onSuccess: (_, action) => {
      setEdit(null);
      toast.success(
        action === "forget" ? "Catatan dilupakan" : "Catatan diperbarui",
      );
      void client.invalidateQueries({ queryKey: memoryKey });
      onChanged();
    },
    onError: (error) => {
      toast.error(displayError(error));
      void client.invalidateQueries({ queryKey: memoryKey });
    },
  });
  return (
    <article className="border-b py-5 first:pt-0 last:border-0">
      {edit ? (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!edit.content.trim()) {
              toast.error("Catatan tidak boleh kosong.");
              return;
            }
            mutation.mutate("save");
          }}
        >
          <label htmlFor={`memory-${memory.id}`} className="sr-only">
            Isi catatan
          </label>
          <Textarea
            id={`memory-${memory.id}`}
            value={edit.content}
            maxLength={1000}
            disabled={mutation.isPending}
            onChange={(e) => setEdit({ ...edit, content: e.target.value })}
            className="min-h-28"
            autoFocus
          />
          <div className="mt-2 flex items-center gap-2">
            <span className="mr-auto text-xs text-muted-foreground">
              {edit.content.length}/1000
            </span>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled={mutation.isPending}
              onClick={() => setEdit(null)}
            >
              Batal
            </Button>
            <Button
              size="sm"
              disabled={mutation.isPending || edit.revision !== memory.revision}
            >
              Simpan
            </Button>
          </div>
          {edit.revision !== memory.revision && (
            <Button
              type="button"
              variant="link"
              size="sm"
              onClick={() =>
                setEdit({ content: memory.content, revision: memory.revision })
              }
            >
              Gunakan versi terbaru
            </Button>
          )}
        </form>
      ) : (
        <>
          <p className="whitespace-pre-wrap break-words text-sm leading-6">
            {memory.content}
          </p>
          <div className="mt-3 flex items-center gap-1">
            <p className="mr-auto text-xs text-muted-foreground">
              {new Date(memory.created_at).toLocaleString("id-ID", {
                dateStyle: "medium",
                timeStyle: "short",
              })}
            </p>
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label="Edit catatan"
              onClick={() =>
                setEdit({ content: memory.content, revision: memory.revision })
              }
              disabled={mutation.isPending}
            >
              <Pencil className="size-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label="Lupakan catatan"
              disabled={mutation.isPending}
              onClick={() => mutation.mutate("forget")}
            >
              <Trash2 className="size-3.5" />
            </Button>
          </div>
          {memory.source_message_id ? (
            <details className="mt-1 text-xs text-muted-foreground">
              <summary className="cursor-pointer">Sumber: pesan chat</summary>
              <p className="mt-2 break-all font-mono">
                {memory.source_message_id}
              </p>
            </details>
          ) : (
            <p className="mt-1 text-xs text-muted-foreground">
              Diperbarui melalui panel
            </p>
          )}
        </>
      )}
    </article>
  );
}
export function MemoryPanel({
  open,
  onOpenChange,
  onChanged,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onChanged: () => void;
}) {
  const query = useMemories(open);
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="flex w-full flex-col sm:max-w-md">
        <SheetHeader>
          <SheetTitle>Memory</SheetTitle>
          <SheetDescription>
            Catatan yang Anda minta untuk diingat, digunakan lintas percakapan.
          </SheetDescription>
        </SheetHeader>
        <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-6">
          {query.isPending ? (
            <p role="status" className="text-sm text-muted-foreground">
              Memuat catatan…
            </p>
          ) : query.isError ? (
            <Button variant="outline" onClick={() => void query.refetch()}>
              Muat ulang catatan
            </Button>
          ) : (
            <>
              <p className="mb-6 text-xs text-muted-foreground">
                {query.data.memories.length} dari 8 catatan · Melupakan catatan
                tidak menghapus chat sebelumnya.
              </p>
              {query.data.memories.length === 0 && (
                <p className="text-sm leading-6 text-muted-foreground">
                  Belum ada catatan. Katakan “Ingat…” di chat untuk menyimpan
                  hal yang penting bagi Anda.
                </p>
              )}
              {query.data.memories.map((memory) => (
                <MemoryItem
                  key={memory.id}
                  memory={memory}
                  onChanged={onChanged}
                />
              ))}
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
