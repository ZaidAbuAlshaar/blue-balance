export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown) {
    const b = body as Record<string, unknown> | null;
    const msg = b && typeof b === 'object' ? String(b.detail ?? b.error ?? JSON.stringify(b)) : String(body);
    super(msg);
    this.status = status;
    this.body = body;
  }
}

export async function api<T = any>(path: string, opts: { method?: string; body?: unknown } = {}): Promise<T> {
  const r = await fetch(path, {
    method: opts.method ?? (opts.body !== undefined ? 'POST' : 'GET'),
    credentials: 'same-origin',
    headers: opts.body !== undefined ? { 'content-type': 'application/json' } : undefined,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  });
  const text = await r.text();
  let data: unknown = text;
  try { data = text ? JSON.parse(text) : null; } catch { /* keep text */ }
  if (!r.ok) throw new ApiError(r.status, data);
  return data as T;
}

export const post = <T = any>(path: string, body: unknown = {}) => api<T>(path, { method: 'POST', body });
