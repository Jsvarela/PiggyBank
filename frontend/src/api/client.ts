const BASE = import.meta.env.VITE_API_URL ?? ''

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

/** Mensaje en español para cada tipo de fallo (nunca "Failed to fetch" ni "[object Object]"). */
function messageFor(status: number, detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (status === 429) return 'Demasiados intentos. Espera un momento e inténtalo de nuevo.'
  if (status >= 500) return 'El servidor tuvo un problema. Inténtalo de nuevo en un momento.'
  if (status === 401) return 'Tu sesión venció. Inicia sesión de nuevo.'
  return 'Hay datos inválidos: revisa los campos e inténtalo de nuevo.'
}

export async function api<T>(path: string, opts: { method?: string; body?: unknown } = {}): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${BASE}/api${path}`, {
      method: opts.method ?? 'GET',
      credentials: 'include',
      headers: opts.body ? { 'Content-Type': 'application/json' } : undefined,
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    })
  } catch {
    // Debe seguir siendo un TypeError: la cola sin conexión lo usa para saber que no hubo red.
    throw new TypeError('No hay conexión con el servidor. Revisa tu internet e inténtalo de nuevo.')
  }
  if (!res.ok) {
    let detail: unknown
    try {
      detail = (await res.json()).detail
    } catch {
      /* respuesta sin JSON */
    }
    throw new ApiError(res.status, messageFor(res.status, detail))
  }
  return res.status === 204 ? (undefined as T) : res.json()
}
