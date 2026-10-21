import { Check, ChevronDown, Loader2, Wrench, X } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import type { ToolActivity as Tool } from "../api";
const labels: Record<string, string> = {
  search_vehicles: "Mencari kendaraan",
  get_vehicle_activity: "Memeriksa aktivitas",
  analyze_fuel_consumption: "Menganalisis BBM",
  get_maintenance_history: "Memeriksa maintenance",
  get_breakdown_history: "Memeriksa breakdown",
  search_knowledge: "Mencari SOP",
  remember_memory: "Menyimpan memory",
  forget_memory: "Melupakan catatan",
};
const formatDate = (date: string) =>
  new Date(date).toLocaleString("id-ID", {
    dateStyle: "medium",
    timeStyle: "short",
  });
function ToolDetail({ tool }: { tool: Tool }) {
  const result = tool.result;
  if (!result)
    return (
      <p className="text-muted-foreground">
        {tool.status === "running"
          ? "Sedang diproses…"
          : "Aktivitas selesai. Hasil dijelaskan dalam jawaban."}
      </p>
    );
  if (result.status === "ERROR")
    return <p>Hasil tidak tersedia · {result.code}</p>;
  const data = result.data;
  return (
    <div className="space-y-3">
      {result.status === "NO_DATA" && <p>Tidak ada data untuk cakupan ini.</p>}
      <dl className="space-y-2">
        <div>
          <dt className="font-medium">Metode</dt>
          <dd className="break-words text-muted-foreground">{result.method}</dd>
        </div>
        {result.observed_period && (
          <div>
            <dt className="font-medium">Periode pengamatan</dt>
            <dd className="text-muted-foreground">
              {formatDate(result.observed_period.start)} –{" "}
              {formatDate(result.observed_period.end)} (akhir tidak termasuk)
            </dd>
          </div>
        )}
        <div>
          <dt className="font-medium">Cakupan depot</dt>
          <dd className="text-muted-foreground">
            {result.depot_filter_basis === "snapshot_depot"
              ? "Snapshot depot saat kejadian"
              : "Depot kendaraan kini"}
            {result.depot_filter
              ? ` · ID ${result.depot_filter}`
              : " · Semua depot"}
          </dd>
        </div>
        {"vehicle" in data && (
          <div>
            <dt className="font-medium">Depot kendaraan kini</dt>
            <dd className="text-muted-foreground">
              {data.vehicle.depot_name} · ID{" "}
              {data.vehicle.current_vehicle_depot}
            </dd>
          </div>
        )}
        {"historical_depot_available" in data && (
          <p>Atribusi depot historis untuk WO/breakdown tidak tersedia.</p>
        )}
        {"analysis" in data && (
          <div>
            <dt className="font-medium">Estimasi full-to-full</dt>
            <dd>
              {data.analysis.liters_per_100_km ?? "Tidak tersedia"}
              {data.analysis.liters_per_100_km !== null
                ? " L/100 km"
                : ""} · {data.analysis.intervals.length} interval
            </dd>
          </div>
        )}
        {"operations" in data && (
          <div>
            <dt className="font-medium">Waktu mesin lengkap</dt>
            <dd>
              {data.operations.complete_engine_on_seconds === null
                ? "Tidak tersedia"
                : `${data.operations.complete_engine_on_seconds} detik`}{" "}
              ·{" "}
              {data.operations.all_selected_sessions_complete
                ? "Cakupan lengkap"
                : "Cakupan tidak lengkap"}
            </dd>
          </div>
        )}
      </dl>
      {result.coverage.length > 0 && (
        <div>
          <p className="font-medium">Cakupan dan keterbatasan</p>
          <ul className="mt-1 list-disc space-y-1 pl-4 text-muted-foreground">
            {result.coverage.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      )}
      {"analysis" in data && data.analysis.coverage.length > 0 && (
        <ul className="space-y-1 text-muted-foreground">
          {data.analysis.coverage.map((o, i) => (
            <li key={i}>
              {o.record_ref.table} #{o.record_ref.id}: {o.reasons.join(", ")}
            </li>
          ))}
        </ul>
      )}
      {"operations" in data && data.operations.coverage.length > 0 && (
        <ul className="space-y-1 text-muted-foreground">
          {data.operations.coverage.map((o, i) => (
            <li key={i}>
              Sesi #{o.record_ref.id}: {o.reasons.join(", ")} · mesin{" "}
              {o.engine_on_seconds ?? "tidak tersedia"}
            </li>
          ))}
        </ul>
      )}
      {"entries" in data && (
        <Collapsible>
          <CollapsibleTrigger className="underline underline-offset-4">
            Pengisian dan kondisi meter
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="mt-2 overflow-x-auto">
              <table className="w-full whitespace-nowrap text-left text-xs">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Depot saat pengisian</th>
                    <th>Jenis</th>
                    <th>Meter</th>
                    <th>Reset</th>
                    <th>Odometer</th>
                  </tr>
                </thead>
                <tbody>
                  {data.entries.map((e) => (
                    <tr key={e.id}>
                      <td>{e.id}</td>
                      <td>{e.depot_id}</td>
                      <td>{e.fill_type}</td>
                      <td>{e.meter_valid ? "Valid" : "Invalid"}</td>
                      <td>{e.reset_baseline ? "Ya" : "Tidak"}</td>
                      <td>{e.odometer_km ?? "Tidak tersedia"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CollapsibleContent>
        </Collapsible>
      )}
      <Collapsible>
        <CollapsibleTrigger className="underline underline-offset-4">
          {result.record_refs.length} referensi record
        </CollapsibleTrigger>
        <CollapsibleContent>
          <ul className="mt-2 font-mono text-xs text-muted-foreground">
            {result.record_refs.map((ref, i) => (
              <li key={i}>
                {ref.table} · {ref.id}
              </li>
            ))}
          </ul>
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}
export function ToolActivity({ tools }: { tools: Tool[] }) {
  if (!tools.length) return null;
  const running = tools.some((t) => t.status === "running");
  return (
    <Collapsible className="mb-3 text-sm">
      <CollapsibleTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="group -ml-2 text-muted-foreground"
        >
          {running ? <Loader2 className="animate-spin" /> : <Wrench />}{" "}
          {running
            ? (labels[tools.find((t) => t.status === "running")!.name] ??
              "Memproses")
            : `${tools.length} aktivitas`}
          <ChevronDown className="size-3 transition-transform group-data-[state=open]:rotate-180" />
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent className="mt-2 space-y-2 border-l pl-4">
        {tools.map((tool) => (
          <Collapsible key={tool.tool_call_id}>
            <CollapsibleTrigger className="flex w-full items-center gap-2 py-2 text-left text-xs">
              {tool.status === "running" ? (
                <Loader2 className="size-3 animate-spin" />
              ) : tool.status === "error" ? (
                <X className="size-3" />
              ) : (
                <Check className="size-3" />
              )}
              {labels[tool.name] ?? tool.name}
              <ChevronDown className="ml-auto size-3" />
            </CollapsibleTrigger>
            <CollapsibleContent className="pb-3 text-xs leading-relaxed">
              <ScrollArea className="max-h-72 [&_[data-slot=scroll-area-viewport]]:max-h-72">
                <div className="pr-4">
                  <ToolDetail tool={tool} />
                </div>
              </ScrollArea>
            </CollapsibleContent>
          </Collapsible>
        ))}
      </CollapsibleContent>
    </Collapsible>
  );
}
