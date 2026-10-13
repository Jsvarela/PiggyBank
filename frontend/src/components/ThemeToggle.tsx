import { useState } from 'react'
import { getMode, nextMode, setMode } from '../lib/theme'

const LABEL = { system: 'Automático (según tu dispositivo)', light: 'Claro', dark: 'Oscuro' }

export default function ThemeToggle() {
  const [mode, setLocal] = useState(getMode)
  return (
    <button
      className="flex w-full items-center justify-between rounded-xl bg-surface p-4 text-left shadow-sm"
      onClick={() => {
        const next = nextMode(mode)
        setMode(next)
        setLocal(next)
      }}
    >
      <span className="font-medium">Tema</span>
      <span className="text-sm text-slate-600">{LABEL[mode]}</span>
    </button>
  )
}
