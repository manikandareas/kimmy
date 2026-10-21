import {
  lazy,
  Suspense,
  useCallback,
  useState,
  useSyncExternalStore,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Brain, Menu, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";

import { NewConversation } from "@/features/chat/components/new-conversation";
import { ThreadList } from "@/features/chat/components/thread-list";
import { chatKeys } from "@/features/chat/api";

import { memoryKey } from "@/features/memory/api";
const Conversation = lazy(() =>
  import("@/features/chat/components/conversation").then((module) => ({
    default: module.Conversation,
  })),
);
const MemoryPanel = lazy(() =>
  import("@/features/memory/components/memory-panel").then((module) => ({
    default: module.MemoryPanel,
  })),
);
const subscribe = (callback: () => void) => {
  window.addEventListener("popstate", callback);
  return () => window.removeEventListener("popstate", callback);
};
const currentThread = () => {
  const value = new URLSearchParams(window.location.search).get("thread");
  return value &&
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
      value,
    )
    ? value
    : null;
};
export function App() {
  const client = useQueryClient();
  const threadId = useSyncExternalStore(subscribe, currentThread);
  const [menuOpen, setMenuOpen] = useState(false);
  const [memoryOpen, setMemoryOpen] = useState(false);
  const navigate = (id: string | null) => {
    const url = new URL(window.location.href);
    if (id) url.searchParams.set("thread", id);
    else url.searchParams.delete("thread");
    window.history.pushState(null, "", url);
    window.dispatchEvent(new PopStateEvent("popstate"));
    setMenuOpen(false);
  };
  const memoryChanged = useCallback(() => {
    void client.invalidateQueries({ queryKey: memoryKey });
  }, [client]);
  const panelChanged = useCallback(() => {
    memoryChanged();
    void client.invalidateQueries({ queryKey: ["chat", "snapshot"] });
  }, [client, memoryChanged]);
  const list = (
    <ThreadList
      activeId={threadId}
      onSelect={navigate}
      onNew={() => navigate(null)}
    />
  );
  return (
    <div className="flex h-dvh overflow-hidden bg-background text-foreground">
      <aside className="hidden w-64 shrink-0 flex-col border-r border-neutral-200/60 bg-neutral-50 md:flex">
        <button
          className="flex h-20 items-center px-6 text-xl font-semibold tracking-tight"
          onClick={() => navigate(null)}
          aria-label="Kimmy, percakapan baru"
        >
          kimmy<span className="ml-0.5 text-neutral-400">.</span>
        </button>
        <div className="min-h-0 flex-1">{list}</div>
        <div className="p-3">
          <Button
            variant="ghost"
            className="w-full justify-start gap-3 font-normal"
            onClick={() => setMemoryOpen(true)}
          >
            <Brain className="size-4" />
            Memory
          </Button>
        </div>
      </aside>
      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 shrink-0 items-center gap-2 px-4 sm:px-6">
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            aria-label="Buka daftar percakapan"
            onClick={() => setMenuOpen(true)}
          >
            <Menu />
          </Button>
          <span className="text-sm font-medium">Kimmy</span>
          <span className="ml-1 rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] text-muted-foreground">
            Demo
          </span>
          <div className="ml-auto flex items-center">
            <Button
              variant="ghost"
              size="icon"
              aria-label="Buka memory"
              className="md:hidden"
              onClick={() => setMemoryOpen(true)}
            >
              <Brain />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              aria-label="Percakapan baru"
              onClick={() => navigate(null)}
            >
              <Plus />
            </Button>
          </div>
        </header>
        <Suspense
          fallback={
            <p role="status" className="p-6 text-sm text-muted-foreground">
              Memuat percakapan…
            </p>
          }
        >
          {threadId ? (
            <Conversation
              key={threadId}
              threadId={threadId}
              onMemoryChange={memoryChanged}
            />
          ) : (
            <NewConversation
              onCreated={(id) => {
                void client.invalidateQueries({ queryKey: chatKeys.threads });
                navigate(id);
              }}
            />
          )}
        </Suspense>
      </main>
      <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
        <SheetContent
          side="left"
          className="flex w-72 flex-col bg-neutral-50 p-0"
        >
          <SheetHeader className="h-20 justify-center px-6">
            <SheetTitle className="text-xl tracking-tight">kimmy.</SheetTitle>
          </SheetHeader>
          <div className="min-h-0 flex-1">{list}</div>
        </SheetContent>
      </Sheet>
      <Suspense fallback={null}>
        <MemoryPanel
          open={memoryOpen}
          onOpenChange={setMemoryOpen}
          onChanged={panelChanged}
        />
      </Suspense>
    </div>
  );
}
