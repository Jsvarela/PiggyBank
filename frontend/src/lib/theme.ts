export type ThemeMode = 'system' | 'light' | 'dark'
const KEY = 'theme'

export const isDark = (mode: ThemeMode, systemPrefersDark: boolean) => (mode === 'system' ? systemPrefersDark : mode === 'dark')
export const nextMode = (mode: ThemeMode): ThemeMode => (mode === 'system' ? 'light' : mode === 'light' ? 'dark' : 'system')

export function getMode(): ThemeMode {
  try {
    const v = localStorage.getItem(KEY)
    return v === 'light' || v === 'dark' ? v : 'system'
  } catch {
    return 'system'
  }
}

// Color de la cabecera (--color-surface en index.css): así la barra de estado del celular no desentona.
export const themeColor = (dark: boolean) => (dark ? '#1e293b' : '#ffffff')

export function applyTheme(mode = getMode()) {
  const dark = isDark(mode, matchMedia('(prefers-color-scheme: dark)').matches)
  document.documentElement.classList.toggle('dark', dark)
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', themeColor(dark))
}

export function setMode(mode: ThemeMode) {
  try {
    localStorage.setItem(KEY, mode)
  } catch {
    /* sin almacenamiento: el cambio dura hasta recargar */
  }
  applyTheme(mode)
}

/** Aplica el tema al abrir y reacciona si el sistema cambia mientras está en automático. */
export function initTheme() {
  applyTheme()
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => applyTheme())
}
