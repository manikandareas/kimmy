import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { getSource, type Citation } from "../api";
import { MessageContent } from "./message-content";
export function SourceDialog({
  citation,
  onClose,
}: {
  citation: Citation | null;
  onClose: () => void;
}) {
  const query = useQuery({
    queryKey: ["chat", "source", citation?.chunk_id],
    queryFn: ({ signal }) => getSource(citation!.chunk_id, signal),
    enabled: !!citation,
  });
  return (
    <Dialog
      open={!!citation}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent className="max-h-[85dvh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader className="pr-5 text-left">
          <DialogTitle className="leading-6">
            {query.data?.title ?? citation?.title ?? "Sumber SOP"}
          </DialogTitle>
          <DialogDescription>
            {citation?.section} · Versi {citation?.version}
          </DialogDescription>
        </DialogHeader>
        {query.isPending ? (
          <p role="status" className="text-sm text-muted-foreground">
            Membuka sumber…
          </p>
        ) : query.data ? (
          <>
            <p className="text-xs text-muted-foreground">
              Berlaku {query.data.effective_date} · {query.data.source}
            </p>
            <MessageContent content={query.data.quote} />
          </>
        ) : (
          <Button variant="outline" onClick={() => void query.refetch()}>
            Muat ulang sumber
          </Button>
        )}
      </DialogContent>
    </Dialog>
  );
}
