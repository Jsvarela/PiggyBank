import { useEffect, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { api } from '../api/client'
import type { Transaction } from '../api/types'
import { useQueryClient } from '@tanstack/react-query'
import { useAccounts, useCategories } from '../api/hooks'
import { flushQueue } from '../lib/offlineQueue'
import { setSession } from '../lib/localCache'
import { EditorContext } from './editor'
import PendingBanner from './PendingBanner'
import Ready from './Ready'
import QuickAdd from './QuickAdd'

const links = [
  ['/', 'Inicio'],
  ['/movimientos', 'Movimientos'],
  ['/presupuestos', 'Presupuestos'],
  ['/metas', 'Metas'],
  ['/mas', 'Más'],
] as const

export default function Layout() {
  // undefined = cerrado, null = nuevo movimiento, Transaction = editar
  const [editing, setEditing] = useState<Transaction | null | undefined>(undefined)
  const qc = useQueryClient()
  const accounts = useAccounts()
  const categories = useCategories()

  // al abrir la app: crea los movimientos recurrentes que ya tocaban (es idempotente)
  useEffect(() => {
    api<{ created: number }>('/sync', { method: 'POST' })
      .then((r) => {
        if (r.created > 0) qc.invalidateQueries()
      })
      .catch(() => {})
  }, [qc])

  // movimientos guardados sin conexión: se envían al abrir, al volver la red y cada minuto
  // (el minuto cubre el caso de un servidor gratuito que aún está despertando)
  useEffect(() => {
    const flush = () =>
      flushQueue()
        .then((sent) => {
          if (sent > 0) qc.invalidateQueries()
        })
        .catch(() => {})
    flush()
    const timer = setInterval(flush, 60_000)
    window.addEventListener('online', flush)
    return () => {
      clearInterval(timer)
      window.removeEventListener('online', flush)
    }
  }, [qc])

  return (
    <EditorContext.Provider value={(tx) => setEditing(tx ?? null)}>
      <div className="min-h-screen bg-slate-50 pb-32 text-slate-900">
        <header className="flex items-center justify-between bg-surface px-4 py-3 shadow-sm">
          <span className="font-semibold">Finanzas</span>
          <button
            className="text-sm text-slate-600"
            onClick={async () => {
              await api('/auth/logout', { method: 'POST' })
              setSession(false)
              qc.clear()
              location.reload()
            }}
          >
            Salir
          </button>
        </header>
        <main className="mx-auto max-w-2xl space-y-4 p-4">
          <PendingBanner />
          <Outlet />
        </main>

        <button
          aria-label="Nuevo movimiento"
          className="fixed bottom-20 right-4 z-10 h-14 w-14 rounded-full bg-emerald-600 text-3xl text-white shadow-lg"
          onClick={() => setEditing(null)}
        >
          +
        </button>
        <nav className="fixed inset-x-0 bottom-0 flex border-t bg-surface">
          {links.map(([to, label]) => (
            <NavLink
              key={to}
              to={to}
              end
              className={({ isActive }) => `flex-1 py-3 text-center text-xs ${isActive ? 'font-semibold text-emerald-700' : 'text-slate-600'}`}
            >
              {label}
            </NavLink>
          ))}
        </nav>
        {editing !== undefined && (
          <Ready of={[accounts, categories]}>
            <QuickAdd tx={editing ?? undefined} onClose={() => setEditing(undefined)} />
          </Ready>
        )}
      </div>
    </EditorContext.Provider>
  )
}
