import { useState } from "react";
import { toast } from "sonner";
import type { Provider } from "../components/model-select";
export type PendingMessage = {
  request_key: string;
  content: string;
  provider?: Provider;
};
type Saved = {
  draft: string;
  pending: PendingMessage | null;
  provider?: Provider;
};
const storageKey = (id: string) => `kimmy:composer:${id}`;
function read(id: string): Saved {
  try {
    const value = JSON.parse(
      localStorage.getItem(storageKey(id)) ?? "null",
    ) as Saved | null;
    if (
      value &&
      typeof value.draft === "string" &&
      (!value.pending ||
        (typeof value.pending.content === "string" &&
          typeof value.pending.request_key === "string"))
    )
      return value;
  } catch {
    /* Unavailable storage or an obsolete draft starts empty. */
  }
  return { draft: "", pending: null };
}
export function useMessageDraft(id: string) {
  const [saved, setSaved] = useState(() => read(id));
  const save = (next: Saved) => {
    try {
      localStorage.setItem(storageKey(id), JSON.stringify(next));
    } catch {
      toast.error(
        "Penyimpanan browser tidak tersedia. Draft tidak dapat dipulihkan setelah halaman ditutup.",
        { id: "draft-storage" },
      );
    }
    setSaved(next);
  };
  return {
    ...saved,
    setProvider: (provider: Provider) => save({ ...saved, provider }),
    setDraft: (draft: string) => save({ ...saved, draft }),
    stage: (content: string) => {
      const pending = {
        content,
        request_key: crypto.randomUUID(),
        provider: saved.provider,
      };
      save({ ...saved, draft: content, pending });
      return pending;
    },
    acknowledge: () => save({ ...saved, draft: "", pending: null }),
    reject: () => save({ ...saved, pending: null }),
  };
}
