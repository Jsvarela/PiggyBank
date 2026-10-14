// Seguimiento de errores sin servicios externos: los errores de JavaScript del navegador se envían
// al servidor y quedan en su log. No hay alertas ni agrupación (para eso existe Sentry).
let last = ''

export async function reportError(error: unknown): Promise<void> {
  const err = error instanceof Error ? error : new Error(typeof error === 'string' ? error : JSON.stringify(error))
  const message = `${err.name}: ${err.message}`.slice(0, 2000)
  if (message === last) return // un bucle de render no debe inundar el log
  last = message
  try {
    await fetch('/api/client-errors', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, stack: err.stack?.slice(0, 8000), url: location.pathname }),
    })
  } catch {
    /* sin red o servidor caído: no hay nada más que hacer */
  }
}

export function initErrorReporting() {
  window.addEventListener('error', (e) => void reportError(e.error ?? e.message))
  window.addEventListener('unhandledrejection', (e) => void reportError(e.reason))
}
