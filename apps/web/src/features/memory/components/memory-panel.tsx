import { useState, useSyncExternalStore } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Item,
  ItemContent,
  ItemActions,
  ItemGroup,
} from "@/components/ui/item";
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
    <Item role="listitem" variant="outline" className="items-start rounded-xl">
      <ItemContent className="min-w-0">
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
                disabled={
                  mutation.isPending || edit.revision !== memory.revision
                }
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
                  setEdit({
                    content: memory.content,
                    revision: memory.revision,
                  })
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
            <ItemActions className="mt-3 flex-wrap">
              <p className="mr-auto text-xs text-muted-foreground">
                {new Date(memory.created_at).toLocaleString("id-ID", {
                  dateStyle: "medium",
                  timeStyle: "short",
                })}
              </p>
              <Button
                variant="ghost"
                size="sm"
                aria-label="Edit catatan"
                onClick={() =>
                  setEdit({
                    content: memory.content,
                    revision: memory.revision,
                  })
                }
                disabled={mutation.isPending}
              >
                <Pencil className="size-3.5" /> Edit
              </Button>
              <Button
                variant="ghost"
                size="sm"
                aria-label="Lupakan catatan"
                disabled={mutation.isPending}
                onClick={() => mutation.mutate("forget")}
              >
                <Trash2 className="size-3.5" /> Lupakan
              </Button>
            </ItemActions>
            <p className="mt-1 text-xs text-muted-foreground">
              {memory.source_message_id
                ? "Disimpan dari percakapan"
                : "Diperbarui melalui panel"}
            </p>
          </>
        )}
      </ItemContent>
    </Item>
  );
}
const media = () => window.matchMedia("(min-width: 768px)");
const subscribeDesktop = (callback: () => void) => {
  const query = media();
  query.addEventListener("change", callback);
  return () => query.removeEventListener("change", callback);
};
const isDesktop = () => media().matches;

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
  const desktop = useSyncExternalStore(
    subscribeDesktop,
    isDesktop,
    () => false,
  );
  const body = (
    <ScrollArea className="min-h-0 flex-1 [&_[data-slot=scroll-area-viewport]]:max-h-[60dvh]">
      <div className="px-1 pb-2 pr-4">
        {query.isPending ? (
          <p role="status" className="py-6 text-sm text-muted-foreground">
            Memuat catatan…
          </p>
        ) : query.isError ? (
          <Button variant="outline" onClick={() => void query.refetch()}>
            Muat ulang catatan
          </Button>
        ) : (
          <>
            {query.data.memories.length === 0 && (
              <div className="rounded-xl border border-dashed p-8 text-center text-sm leading-6 text-muted-foreground">
                Belum ada catatan. Katakan “Ingat…” di chat untuk menyimpan hal
                yang penting bagi Anda.
              </div>
            )}
            <ItemGroup className="gap-3">
              {query.data.memories.map((memory) => (
                <MemoryItem
                  key={memory.id}
                  memory={memory}
                  onChanged={onChanged}
                />
              ))}
            </ItemGroup>
          </>
        )}
      </div>
    </ScrollArea>
  );
  const description =
    "Catatan yang Anda minta untuk diingat, digunakan lintas percakapan.";
  return desktop ? (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[85dvh] flex-col sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Memory</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        {body}
      </DialogContent>
    </Dialog>
  ) : (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent className="max-h-[90dvh]">
        <DrawerHeader className="text-left">
          <DrawerTitle>Memory</DrawerTitle>
          <DrawerDescription>{description}</DrawerDescription>
        </DrawerHeader>
        <div className="min-h-0 overflow-hidden px-4">{body}</div>
        <div className="p-4">
          <DrawerClose asChild>
            <Button variant="outline" className="w-full">
              Tutup
            </Button>
          </DrawerClose>
        </div>
      </DrawerContent>
    </Drawer>
  );
}
