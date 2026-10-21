import { useQuery } from "@tanstack/react-query";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { apiGet } from "@/lib/api-client";
import type { components } from "@/types/api.generated";

export type Provider = "openai" | "openrouter";
export function ModelSelect({
  value,
  onChange,
  disabled,
}: {
  value?: Provider;
  onChange: (value: Provider) => void;
  disabled?: boolean;
}) {
  const query = useQuery({
    queryKey: ["chat", "models"],
    queryFn: ({ signal }) =>
      apiGet<components["schemas"]["ModelOptions"]>("/chat/models", signal),
    staleTime: 60_000,
  });
  return (
    <Select
      value={value ?? query.data?.default_provider ?? ""}
      onValueChange={(v) => onChange(v as Provider)}
      disabled={disabled || !query.data}
    >
      <SelectTrigger
        aria-label="Pilih model"
        size="sm"
        className="w-auto max-w-36 shrink-0 rounded-full border-0 bg-transparent px-2 text-xs text-muted-foreground shadow-none hover:bg-neutral-100"
      >
        <SelectValue
          placeholder={query.isError ? "Model tidak tersedia" : "Memuat model…"}
        />
      </SelectTrigger>
      <SelectContent position="popper" align="end">
        {query.data?.models.map((model) => (
          <SelectItem
            key={model.provider}
            value={model.provider}
            disabled={!model.available}
          >
            <span>
              {model.label}
              <span className="sr-only">
                {" "}
                · {model.provider === "openai" ? "OpenAI" : "OpenRouter"}
                {!model.available ? " · Belum dikonfigurasi" : ""}
              </span>
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
