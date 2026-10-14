// Lo mínimo para registrar un gasto sin conexión: la lista de cuentas y categorías de la última
// vez que hubo red, y saber si ya había una sesión (para no mostrar el login sin internet).
const PREFIX = 'cache:'
const SESSION = 'hadSession'

export function readCache<T>(key: string): T | undefined {
  try {
    const raw = localStorage.getItem(PREFIX + key)
    return raw ? (JSON.parse(raw) as T) : undefined
  } catch {
    return undefined
  }
}

export function writeCache(key: string, value: unknown) {
  try {
    localStorage.setItem(PREFIX + key, JSON.stringify(value))
  } catch {
    /* sin almacenamiento: solo se pierde el modo offline */
  }
}

export const hadSession = () => {
  try {
    return localStorage.getItem(SESSION) !== null
  } catch {
    return false
  }
}

/** Quién tenía la sesión la última vez (sirve sin internet, cuando aún no se puede preguntar al servidor). */
export function sessionUserId(): number | null {
  try {
    const n = Number(localStorage.getItem(SESSION))
    return Number.isInteger(n) && n > 0 ? n : null
  } catch {
    return null
  }
}

export function setSession(active: boolean, userId?: number) {
  try {
    if (active) localStorage.setItem(SESSION, String(userId ?? sessionUserId() ?? 1))
    else {
      localStorage.removeItem(SESSION)
      Object.keys(localStorage).filter((k) => k.startsWith(PREFIX)).forEach((k) => localStorage.removeItem(k))
    }
  } catch {
    /* ver arriba */
  }
}
