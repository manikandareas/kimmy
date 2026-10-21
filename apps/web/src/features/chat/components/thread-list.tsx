import { MessageSquare, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { useThreads } from "../api";
export function ThreadList({
  activeId,
  onSelect,
  onNew,
}: {
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
}) {
  const query = useThreads();
  return (
    <div className="flex h-full min-h-0 flex-col">
      <Button
        variant="ghost"
        className="mx-3 mb-7 justify-start gap-3"
        onClick={onNew}
      >
        <Plus className="size-4" />
        Percakapan baru
      </Button>
      <p className="mb-2 px-6 text-xs text-muted-foreground">Percakapan</p>
      <ScrollArea className="thread-scroll min-h-0 min-w-0 flex-1">
        <nav className="space-y-1 px-3 pb-6" aria-label="Daftar percakapan">
          {query.data?.pages
            .flatMap((p) => p.threads)
            .filter((t, i, all) => all.findIndex((x) => x.id === t.id) === i)
            .map((thread) => (
              <Button
                key={thread.id}
                variant="ghost"
                className={cn(
                  "w-full justify-start gap-2 font-normal",
                  activeId === thread.id && "bg-neutral-200/60",
                )}
                aria-current={activeId === thread.id ? "page" : undefined}
                onClick={() => onSelect(thread.id)}
              >
                <MessageSquare className="size-3.5 shrink-0 text-muted-foreground" />
                <span className="truncate">{thread.title}</span>
              </Button>
            ))}
          {query.isPending && (
            <p role="status" className="px-3 text-xs text-muted-foreground">
              Memuat…
            </p>
          )}
          {query.isError && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => void query.refetch()}
            >
              Muat ulang
            </Button>
          )}
          {query.hasNextPage && (
            <Button
              variant="ghost"
              size="sm"
              disabled={query.isFetchingNextPage}
              onClick={() => void query.fetchNextPage()}
            >
              Percakapan lainnya
            </Button>
          )}
        </nav>
      </ScrollArea>
    </div>
  );
}
