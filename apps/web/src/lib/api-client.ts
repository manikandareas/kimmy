export async function apiGet<T>(
  path: string,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(`/api${path}`, {
    signal: signal ?? AbortSignal.timeout(10000),
    headers: { Accept: "application/json" },
  });

  if (!response.ok)
    throw new Error(`Layanan belum tersedia (${response.status}).`);

  return response.json() as Promise<T>;
}
