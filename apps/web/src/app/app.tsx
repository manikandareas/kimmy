import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { apiGet } from "@/lib/api-client";
import type { components } from "@/types/api.generated";

export function App() {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () =>
      apiGet<components["schemas"]["HealthResponse"]>("/health/ready"),
  });

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center px-6 py-12">
      <p className="mb-5 text-sm font-semibold tracking-widest text-slate-500">
        KIMMY · DEMO
      </p>
      <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
        Asisten operasional armada.
      </h1>
      <p className="mt-5 max-w-xl text-lg leading-relaxed text-slate-600">
        Fondasi aplikasi sudah tersedia. Percakapan, analisis kendaraan, dan
        referensi SOP akan hadir pada tahap berikutnya.
      </p>
      <section
        className="mt-10 rounded-xl border border-slate-200 bg-white p-6"
        aria-label="Status layanan"
      >
        <div role="status" aria-live="polite">
          <h2 className="font-medium">
            {health.isPending
              ? "Memeriksa layanan…"
              : health.isError
                ? "Layanan belum terhubung"
                : "Layanan siap"}
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            {health.isError
              ? health.error.message
              : health.isPending
                ? "Mohon tunggu sebentar."
                : "Koneksi aplikasi dan database tersedia."}
          </p>
        </div>
        <Button
          className="mt-5"
          variant="outline"
          disabled={health.isFetching}
          onClick={() => void health.refetch()}
        >
          Periksa ulang
        </Button>
      </section>
      <p className="mt-6 text-xs text-slate-500">
        Lingkungan demo menggunakan data simulasi.
      </p>
    </main>
  );
}
