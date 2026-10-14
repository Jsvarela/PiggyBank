import type { ReactElement } from 'react'

// Iconos de la barra inferior: trazos simples en SVG propio (sin dependencias nuevas).
const PATHS = {
  inicio: <path d="M3 11.5 12 4l9 7.5V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z" />,
  movimientos: <path d="M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01" />,
  presupuestos: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 3v9h9" />
    </>
  ),
  metas: (
    <>
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="5" />
      <circle cx="12" cy="12" r="1" />
    </>
  ),
  mas: <path d="M5 12h.01M12 12h.01M19 12h.01" strokeWidth="3.5" />,
} satisfies Record<string, ReactElement>

export type NavIconName = keyof typeof PATHS

export default function NavIcon({ name }: { name: NavIconName }) {
  return (
    <svg aria-hidden viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      {PATHS[name]}
    </svg>
  )
}
