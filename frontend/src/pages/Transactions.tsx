import { useState } from 'react'
import { useAccounts, useCategories, useTransactions } from '../api/hooks'
import { TX_TYPES, type TransactionFilters, type TxType } from '../api/types'
import Loading from '../components/Loading'
import TransactionRow from '../components/TransactionRow'

const PAGE = 20
// text-base (16px): en iPhone, un campo con letra menor hace zoom a toda la página al tocarlo
const input = 'rounded-lg border border-slate-300 bg-surface p-2 text-base'

export default function Transactions() {
  const [f, setF] = useState<TransactionFilters>({ limit: PAGE, offset: 0 })
  const accounts = useAccounts().data ?? []
  const categories = useCategories().data ?? []
  const { data, isFetching, isLoading, isError } = useTransactions(f)
  const total = data?.total ?? 0

  // cambiar un filtro vuelve a la primera página
  const set = (patch: Partial<TransactionFilters>) => setF({ ...f, ...patch, offset: 0 })
  const num = (v: string) => (v ? Number(v) : undefined)

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2">
        <label className="text-xs text-slate-600">
          Desde
          <input type="date" className={`mt-0.5 w-full ${input}`} value={f.from ?? ''} onChange={(e) => set({ from: e.target.value || undefined })} />
        </label>
        <label className="text-xs text-slate-600">
          Hasta
          <input type="date" className={`mt-0.5 w-full ${input}`} value={f.to ?? ''} onChange={(e) => set({ to: e.target.value || undefined })} />
        </label>
        <select aria-label="Cuenta" className={input} value={f.account_id ?? ''} onChange={(e) => set({ account_id: num(e.target.value) })}>
          <option value="">Todas las cuentas</option>
          {accounts.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </select>
        <select aria-label="Categoría" className={input} value={f.category_id ?? ''} onChange={(e) => set({ category_id: num(e.target.value) })}>
          <option value="">Todas las categorías</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <select aria-label="Tipo" className={input} value={f.type ?? ''} onChange={(e) => set({ type: (e.target.value || undefined) as TxType | undefined })}>
          <option value="">Todos los tipos</option>
          {(Object.keys(TX_TYPES) as TxType[]).map((t) => (
            <option key={t} value={t}>
              {TX_TYPES[t]}
            </option>
          ))}
        </select>
        <input placeholder="Buscar texto" className={input} value={f.q ?? ''} onChange={(e) => set({ q: e.target.value || undefined })} />
      </div>

      <section className="rounded-xl bg-surface p-4 shadow-sm">
        {isLoading && <Loading />}
        {isError && !data && <p className="text-sm text-red-600">No se pudieron cargar los movimientos. Revisa tu conexión.</p>}
        {data?.items.length === 0 && (
          <p className="text-sm text-slate-500">{f.q || f.from || f.to || f.account_id || f.category_id || f.type ? 'Ningún movimiento coincide con los filtros.' : 'Aún no hay movimientos. Usa el botón «+» para registrar el primero.'}</p>
        )}
        <ul className={`divide-y ${isFetching ? 'opacity-60' : ''}`}>
          {data?.items.map((t) => (
            <TransactionRow key={t.id} tx={t} />
          ))}
        </ul>
      </section>

      <div className="flex items-center justify-between text-sm">
        <button className="rounded-lg border px-3 py-2 disabled:opacity-40" disabled={f.offset === 0} onClick={() => setF({ ...f, offset: Math.max(0, f.offset - PAGE) })}>
          Anterior
        </button>
        <span>{total === 0 ? '0' : `${f.offset + 1}–${Math.min(f.offset + PAGE, total)} de ${total}`}</span>
        <button className="rounded-lg border px-3 py-2 disabled:opacity-40" disabled={f.offset + PAGE >= total} onClick={() => setF({ ...f, offset: f.offset + PAGE })}>
          Siguiente
        </button>
      </div>
    </div>
  )
}
