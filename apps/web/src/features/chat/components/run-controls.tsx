import { RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Run } from "../api";
import { useRunCommand } from "../hooks/use-run-command";

export function RunControls({ threadId, run }: { threadId: string; run: Run }) {
  const command = useRunCommand(threadId, run, "retry");
  if (!["failed", "cancelled"].includes(run.status)) return null;
  return (
    <div className="mt-4 flex items-center gap-3 text-xs text-muted-foreground">
      {run.status === "cancelled" && <span>Respons dihentikan.</span>}
      {run.attempts >= 3 ? (
        <span>
          Batas 3 percobaan tercapai. Kirim pesan baru untuk melanjutkan.
        </span>
      ) : (
        <Button
          variant="outline"
          size="sm"
          disabled={command.isPending}
          onClick={() => command.mutate()}
        >
          <RotateCcw className="size-3" />
          Coba lagi
        </Button>
      )}
    </div>
  );
}
