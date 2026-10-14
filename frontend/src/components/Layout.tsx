import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { api } from '../api/client'
import type { Transaction } from '../api/types'
import { useQueryClient } from '@tanstack/react-query'
import { useAccounts, useCategories } from '../api/hooks'
import { flushQueue } from '../lib/offlineQueue'
import { setSession } from '../lib/localCache'
import { EditorContext } from './editor'
import PendingBanner from './PendingBanner'
import Ready from './Ready'
import VerifyBanner from './VerifyBanner'
import QuickAdd from './QuickAdd'

const links = [
  ['/', 'Inicio'],
  ['/movimientos', 'Movimientos'],
  ['/presupuestos', 'Presupuestos'],
  ['/metas', 'Metas'],
  ['/mas', 'Más'],
] as const

const TITLES: Record<string, string> = {
  '/movimientos': 'Movimientos',
  '/presupuestos': 'Presupuestos',
  '/metas': 'Metas',
  '/mas': 'Más',
  '/recurrentes': 'Recurrentes',
  '/cuentas': 'Cuentas',
  '/categorias': 'Categorías',
  '/importar': 'Importar extracto',
  '/cuenta': 'Cuenta',
}
const SUBPAGES = new Set(['/recurrentes', '/cuentas', '/categorias', '/importar', '/cuenta'])

export default function Layout() {
  const { pathname } = useLocation()
  const isSub = SUBPAGES.has(pathname)
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
        <header className="bg-surface shadow-sm">
          <div className="mx-auto flex max-w-2xl items-center justify-between px-4 py-3">
            <span className="flex items-baseline gap-2">
              {isSub && (
                <Link to="/mas" className="text-sm text-slate-600" aria-label="Volver a Más">
                  ‹ Más
                </Link>
              )}
              <h1 className="font-semibold">{TITLES[pathname] ?? 'Finanzas'}</h1>
            </span>
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
          </div>
        </header>
        <main className="mx-auto max-w-2xl space-y-4 p-4">
          <VerifyBanner />
          <PendingBanner />
          <Outlet />
        </main>

        {/* el botón "+" se alinea con el contenido, no con el borde de la pantalla */}
        <div className="pointer-events-none fixed inset-x-0 bottom-20 z-10">
          <div className="mx-auto flex max-w-2xl justify-end px-4">
            <button
              aria-label="Nuevo movimiento"
              className="pointer-events-auto h-14 w-14 rounded-full bg-brand text-3xl text-white shadow-lg"
              onClick={() => setEditing(null)}
            >
              +
            </button>
          </div>
        </div>
        <nav className="fixed inset-x-0 bottom-0 border-t bg-surface">
          <div className="mx-auto flex max-w-2xl">
            {links.map(([to, label]) => (
              <NavLink
                key={to}
                to={to}
                end
                className={({ isActive }) => {
                  const active = isActive || (to === '/mas' && isSub) // las subpantallas pertenecen a "Más"
                  return `flex-1 py-3 text-center text-xs ${active ? 'font-semibold text-emerald-700' : 'text-slate-600'}`
                }}
              >
                {label}
              </NavLink>
            ))}
          </div>
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
