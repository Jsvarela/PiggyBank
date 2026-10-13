import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { api } from '../api/client'
import type { Transaction } from '../api/types'
import { useQueryClient } from '@tanstack/react-query'
import { EditorContext } from './editor'
import QuickAdd from './QuickAdd'

const links = [
  ['/', 'Inicio'],
  ['/movimientos', 'Movimientos'],
  ['/cuentas', 'Cuentas'],
  ['/categorias', 'Categorías'],
] as const

export default function Layout() {
  // undefined = cerrado, null = nuevo movimiento, Transaction = editar
  const [editing, setEditing] = useState<Transaction | null | undefined>(undefined)
  const qc = useQueryClient()

  return (
    <EditorContext.Provider value={(tx) => setEditing(tx ?? null)}>
      <div className="min-h-screen bg-slate-50 pb-32 text-slate-900">
        <header className="flex items-center justify-between bg-white px-4 py-3 shadow-sm">
          <span className="font-semibold">Finanzas</span>
          <button
            className="text-sm text-slate-600"
            onClick={async () => {
              await api('/auth/logout', { method: 'POST' })
              qc.clear()
              location.reload()
            }}
          >
            Salir
          </button>
        </header>
        <main className="mx-auto max-w-2xl p-4">
          <Outlet />
        </main>

        <button
          aria-label="Nuevo movimiento"
          className="fixed bottom-20 right-4 z-10 h-14 w-14 rounded-full bg-emerald-600 text-3xl text-white shadow-lg"
          onClick={() => setEditing(null)}
        >
          +
        </button>
        <nav className="fixed inset-x-0 bottom-0 flex border-t bg-white">
          {links.map(([to, label]) => (
            <NavLink
              key={to}
              to={to}
              end
              className={({ isActive }) => `flex-1 py-3 text-center text-sm ${isActive ? 'font-semibold text-emerald-700' : 'text-slate-600'}`}
            >
              {label}
            </NavLink>
          ))}
        </nav>
        {editing !== undefined && <QuickAdd tx={editing ?? undefined} onClose={() => setEditing(undefined)} />}
      </div>
    </EditorContext.Provider>
  )
}
