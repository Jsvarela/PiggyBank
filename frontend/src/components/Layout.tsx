import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { api } from '../api/client'
import type { Transaction } from '../api/types'
import { useQueryClient } from '@tanstack/react-query'
import { useAccounts, useCategories, useUserId } from '../api/hooks'
import { flushQueue } from '../lib/offlineQueue'
import { setSession } from '../lib/localCache'
import { EditorContext } from './editor'
import PendingBanner from './PendingBanner'
import Ready from './Ready'
import VerifyBanner from './VerifyBanner'
import NavIcon from './NavIcon'
import QuickAdd from './QuickAdd'

const links = [
  ['/', 'Inicio', 'inicio'],
  ['/movimientos', 'Movimientos', 'movimientos'],
  ['/presupuestos', 'Presupuestos', 'presupuestos'],
  ['/metas', 'Metas', 'metas'],
  ['/mas', 'Más', 'mas'],
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
  '/invitar': 'Invitar',
}
const SUBPAGES = new Set(['/recurrentes', '/cuentas', '/categorias', '/importar', '/cuenta', '/invitar'])

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
  // Solo se envía lo de ESTA persona: en un celular compartido, lo de otra jamás va a mi cuenta.
  const userId = useUserId()
  useEffect(() => {
    if (userId === null) return
    const flush = () =>
      flushQueue(userId)
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
  }, [qc, userId])

  return (
    <EditorContext.Provider value={(tx) => setEditing(tx ?? null)}>
      <div className="min-h-dvh bg-slate-50 pb-40 text-slate-900">
        <header className="bg-surface pt-[env(safe-area-inset-top)] shadow-sm">
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
        <div className="pointer-events-none fixed inset-x-0 bottom-[calc(5.5rem+env(safe-area-inset-bottom))] z-10">
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
        <nav className="fixed inset-x-0 bottom-0 border-t bg-surface pb-[env(safe-area-inset-bottom)]">
          <div className="mx-auto flex max-w-2xl">
            {/* cada pestaña mide 64 px de alto (el mínimo cómodo para el pulgar es 48) y trae ícono + nombre */}
            {links.map(([to, label, icon]) => (
              <NavLink key={to} to={to} end className="flex min-h-16 min-w-0 flex-1 flex-col items-center justify-center gap-0.5 px-0.5 py-1.5">
                {({ isActive }) => {
                  const active = isActive || (to === '/mas' && isSub) // las subpantallas pertenecen a "Más"
                  return (
                    <>
                      <span className={`flex h-8 w-14 items-center justify-center rounded-full ${active ? 'bg-brand/15 text-emerald-700' : 'text-slate-600'}`}>
                        <NavIcon name={icon} />
                      </span>
                      <span className={`text-[11px] leading-tight max-[340px]:text-[10px] ${active ? 'font-semibold text-emerald-700' : 'text-slate-600'}`}>{label}</span>
                    </>
                  )
                }}
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
