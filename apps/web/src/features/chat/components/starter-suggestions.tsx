import {
  Activity,
  Fuel,
  Search,
  ShieldCheck,
  TriangleAlert,
  Wrench,
} from "lucide-react";
import { Suggestion, Suggestions } from "@/components/ai-elements/suggestion";

const period =
  "1 September 2026 pukul 00.00 sampai 1 Oktober 2026 pukul 00.00 (akhir tidak termasuk), zona waktu Asia/Makassar";
const suggestions = [
  {
    label: "Cek kesiapan armada",
    icon: Search,
    prompt:
      "Cari kendaraan yang saat ini breakdown, maintenance, atau maintenance pending. Ringkas per unit: depot kini, status teknis, dan alasan perlunya perhatian. Bedakan maintenance pending dari kendaraan yang benar-benar berhenti.",
  },
  {
    label: "Bedah konsumsi BBM",
    icon: Fuel,
    prompt: `Analisis BBM KM-001 untuk ${period}. Bedakan belanja pengisian dari estimasi konsumsi full-to-full. Jelaskan pengaruh partial/unknown, meter invalid, reset baseline, dan perpindahan depot. Jangan batasi ke depot kini; sertakan cakupan dan referensi record.`,
  },
  {
    label: "Tinjau aktivitas kendaraan",
    icon: Activity,
    prompt: `Tinjau aktivitas KM-004 untuk ${period}. Ringkas perjalanan, jarak, waktu mesin menyala, dan idle yang tersedia. Bedakan sesi lengkap dan parsial; jangan mengganti jam mesin dengan durasi trip atau nilai tidak tersedia dengan nol.`,
  },
  {
    label: "Periksa riwayat perawatan",
    icon: Wrench,
    prompt: `Periksa riwayat dan jadwal maintenance KM-001 untuk ${period}. Ringkas status work order dan biaya tercatat. Jelaskan pekerjaan yang memerlukan perhatian dan bedakan depot kendaraan kini dari atribusi depot historis yang tidak tersedia.`,
  },
  {
    label: "Telusuri breakdown",
    icon: TriangleAlert,
    prompt: `Telusuri breakdown KM-004 untuk ${period}. Ringkas komponen, gejala, tingkat keparahan, penyebab terkonfirmasi bila ada, serta downtime tanpa menghitung interval overlap dua kali. Cari SOP penanganan yang relevan dan sertakan sumbernya.`,
  },
  {
    label: "Investigasi BBM dengan SOP",
    icon: ShieldCheck,
    prompt: `Bantu investigasi BBM KM-001 untuk ${period}. Periksa konsumsi, aktivitas mesin/idle, riwayat maintenance, dan breakdown, lalu hubungkan dengan SOP investigasi yang relevan. Pisahkan temuan, keterbatasan data, dan langkah pemeriksaan berikutnya; jangan menyimpulkan penyebab hanya dari korelasi. Sertakan sumber SOP dan referensi record.`,
  },
];

export function StarterSuggestions({
  onSelect,
  disabled,
}: {
  onSelect: (prompt: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className="mb-6">
      <Suggestions
        aria-label="Saran pertanyaan armada"
        className="w-full flex-wrap justify-start gap-2"
      >
        {suggestions.map(({ label, icon: Icon, prompt }) => (
          <Suggestion
            key={label}
            suggestion={prompt}
            onClick={onSelect}
            disabled={disabled}
            className="h-9 border-neutral-200 bg-white text-xs font-normal shadow-none hover:bg-neutral-50"
          >
            <Icon className="size-3.5 text-muted-foreground" />
            {label}
          </Suggestion>
        ))}
      </Suggestions>
    </div>
  );
}
