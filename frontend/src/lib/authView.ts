import { ApiError } from '../api/client'
import type { User } from '../api/types'

/**
 * Qué pantalla mostrar al abrir la app. Solo un 401 del servidor significa "ya no hay sesión".
 * Cualquier otro fallo (el servidor gratuito dormido responde 502/503, o no hay internet) NO es motivo
 * para pedir la contraseña de nuevo: si ya había una sesión, se abre la app.
 */
export function authView(s: { user: User | undefined; isLoading: boolean; error: unknown; hadSession: boolean }) {
  if (s.user) return 'app'
  if (s.isLoading) return 'loading'
  if (s.error instanceof ApiError && s.error.status === 401) return 'login'
  return s.hadSession ? 'app' : 'login'
}
