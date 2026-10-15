import { Link } from 'react-router-dom'
import { useLoans } from '../api/hooks'
import type { Loan } from '../api/types'
import { todayBogota } from '../lib/dates'
import { formatDate } from '../lib/format'
import { formatCOP } from '../lib/money'

const left = (l: Loan) => l.expected_amount - l.received

/** Préstamos y deudas pendientes en Inicio (son fáciles de olvidar). No aparece si no hay ninguno. */
export default function LoansSummary({ limit = 3 }: { limit?: number }) {
  const pending = (useLoans().data ?? []).filter((l) => !l.paid) // ya vienen ordenados por fecha
  if (pending.length === 0) return null
  const today = todayBogota()
  const owed = pending.filter((l) => l.direction === 'lent')
  const debts = pending.filter((l) => l.direction === 'borrowed')
  const sum = (ls: Loan[]) => formatCOP(ls.reduce((s, l) => s + left(l), 0))

  return (
    <section className="rounded-xl bg-surface p-4 shadow-sm">
      <div className="mb-2 flex flex-wrap items-baseline justify-between gap-x-3">
        <h2 className="font-medium">Préstamos</h2>
        <span className="text-sm text-slate-600">
          {owed.length > 0 && <span className="whitespace-nowrap">Te deben {sum(owed)}</span>}
          {owed.length > 0 && debts.length > 0 && ' · '}
          {debts.length > 0 && <span className="whitespace-nowrap">Debes {sum(debts)}</span>}
        </span>
      </div>
      <ul className="divide-y">
        {pending.slice(0, limit).map((l) => (
          <li key={l.id} className="flex items-start justify-between gap-3 py-2">
            <span className="min-w-0">
              <span className="line-clamp-2 [overflow-wrap:anywhere]">{l.person}</span>
              <span className="block whitespace-nowrap text-xs text-slate-500">{l.direction === 'lent' ? 'te debe' : 'le debes'}</span>
              <span className={`block text-xs ${l.due_date && l.due_date < today ? 'text-red-700' : 'text-slate-500'}`}>
                {l.due_date ? `${l.due_date < today ? 'Vencido · ' : ''}${formatDate(l.due_date)}` : 'Sin fecha'}
              </span>
            </span>
            <span className="shrink-0 whitespace-nowrap">{formatCOP(left(l))}</span>
          </li>
        ))}
      </ul>
      <Link to="/prestamos" className="mt-2 block text-sm text-slate-600 underline">
        {pending.length > limit ? `Ver los ${pending.length} pendientes` : 'Ver préstamos'}
      </Link>
    </section>
  )
}
