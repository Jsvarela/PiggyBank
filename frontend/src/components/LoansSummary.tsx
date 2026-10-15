import { Link } from 'react-router-dom'
import { useLoans } from '../api/hooks'
import { todayBogota } from '../lib/dates'
import { formatDate } from '../lib/format'
import { formatCOP } from '../lib/money'

/** Préstamos por cobrar en Inicio (son fáciles de olvidar). No aparece si no hay ninguno pendiente. */
export default function LoansSummary({ limit = 3 }: { limit?: number }) {
  const pending = (useLoans().data ?? []).filter((l) => !l.paid) // ya vienen ordenados por fecha de cobro
  if (pending.length === 0) return null
  const today = todayBogota()

  return (
    <section className="rounded-xl bg-surface p-4 shadow-sm">
      <div className="mb-2 flex items-baseline justify-between gap-3">
        <h2 className="font-medium">Te deben</h2>
        <span className="whitespace-nowrap text-sm text-slate-600">{formatCOP(pending.reduce((s, l) => s + l.expected_amount, 0))}</span>
      </div>
      <ul className="divide-y">
        {pending.slice(0, limit).map((l) => (
          <li key={l.id} className="flex items-start justify-between gap-3 py-2">
            <span className="min-w-0">
              <span className="block [overflow-wrap:anywhere]">{l.person}</span>
              <span className={`block text-xs ${l.due_date && l.due_date < today ? 'text-red-700' : 'text-slate-500'}`}>
                {l.due_date ? `${l.due_date < today ? 'Vencido · ' : ''}${formatDate(l.due_date)}` : 'Sin fecha'}
              </span>
            </span>
            <span className="shrink-0 whitespace-nowrap">{formatCOP(l.expected_amount)}</span>
          </li>
        ))}
      </ul>
      <Link to="/prestamos" className="mt-2 block text-sm text-slate-600 underline">
        {pending.length > limit ? `Ver los ${pending.length} préstamos` : 'Ver préstamos'}
      </Link>
    </section>
  )
}
