const messages: Record<string, string> = {
  MEMORY_DUPLICATE: "Catatan yang sama sudah tersimpan.",
  MEMORY_CAPACITY:
    "Delapan catatan sudah aktif. Edit atau lupakan salah satunya terlebih dahulu.",
  THREAD_BUSY: "Tunggu jawaban yang sedang diproses sebelum mengirim lagi.",
  THREAD_NOT_FOUND: "Percakapan ini tidak ditemukan.",
  REQUEST_KEY_CONFLICT:
    "Permintaan ini sudah digunakan. Muat ulang percakapan.",
  INVALID_INPUT: "Periksa kembali isian Anda.",
  MEMORY_CONFLICT:
    "Catatan sudah berubah. Muat versi terbaru sebelum menyimpan.",
  MEMORY_REVISION_CONFLICT:
    "Catatan sudah berubah. Muat versi terbaru sebelum menyimpan.",
  MEMORY_CHANGED:
    "Memory berubah saat jawaban diproses. Kirim pesan baru untuk memakai catatan terbaru.",
  MEMORY_NOT_FOUND: "Catatan sudah diubah atau dilupakan. Muat ulang panel.",
  AGENT_TIMEOUT: "Jawaban melewati batas waktu. Silakan kirim pesan baru.",
  AGENT_LIMIT_EXCEEDED:
    "Analisis mencapai batas proses. Coba persempit pertanyaan.",
  AGENT_EXECUTION_FAILED: "Jawaban belum berhasil diproses. Silakan coba lagi.",
};
export function errorMessage(code?: string | null) {
  return (
    (code && messages[code]) ||
    "Layanan belum dapat menyelesaikan permintaan. Silakan coba lagi."
  );
}
export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
  ) {
    super(errorMessage(code));
  }
}
export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const signal = options.signal
    ? AbortSignal.any([options.signal, AbortSignal.timeout(15000)])
    : AbortSignal.timeout(15000);
  const response = await fetch(`/api${path}`, {
    ...options,
    signal,
    headers: {
      Accept: "application/json",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { code?: string };
    throw new ApiError(response.status, body.code || "SERVICE_UNAVAILABLE");
  }
  return response.json() as Promise<T>;
}
export const apiGet = <T>(path: string, signal?: AbortSignal) =>
  apiRequest<T>(path, { signal });
export function displayError(error: unknown) {
  return error instanceof ApiError
    ? error.message
    : "Koneksi terputus. Periksa jaringan Anda, lalu coba lagi.";
}
