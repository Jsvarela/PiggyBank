import { useAccounts, useCategories, useUpcoming } from '../api/hooks'
import type { UpcomingPayment } from '../api/types'
import { formatDate } from '../lib/format'
import { formatCOP } from '../lib/money'
import Loading from './Loading'

/** Un pago diario ocuparía 30 filas: se muestra una vez por regla, con la próxima fecha y cuántas veces se repite. */
function groupByRule(items: UpcomingPayment[]): { next: UpcomingPayment; times: number }[] {
  const groups = new Map<number, { next: UpcomingPayment; times: number }>()
  for (const p of items) {
    const g = groups.get(p.rule_id)
    if (g) g.times += 1
    else groups.set(p.rule_id, { next: p, times: 1 })
  }
  return [...groups.values()].sort((a, b) => a.next.date.localeCompare(b.next.date))
}

/** Próximos pagos de las reglas recurrentes (los siguientes 30 días). */
export default function UpcomingList({ limit }: { limit?: number }) {
  const { data = [], isLoading } = useUpcoming(30)
  const accounts = useAccounts().data ?? []
  const categories = useCategories().data ?? []
  const groups = groupByRule(data)
  const items = limit ? groups.slice(0, limit) : groups
  if (isLoading) return <Loading />
  if (items.length === 0) return <p className="text-sm text-slate-500">Sin pagos programados en los próximos 30 días.</p>

  return (
    <ul className="divide-y">
      {items.map(({ next: p, times }) => (
        <li key={p.rule_id} className="flex items-start justify-between gap-3 py-2">
          <span className="min-w-0">
            <span className="line-clamp-2 [overflow-wrap:anywhere]">
              {p.description || categories.find((c) => c.id === p.category_id)?.name || 'Transferencia'}
            </span>
            <span className="line-clamp-2 text-xs text-slate-500 [overflow-wrap:anywhere]">
              {formatDate(p.date)} · {accounts.find((a) => a.id === p.account_id)?.name}
              {times > 1 && ` · se repite ${times} veces`}
            </span>
          </span>
          <span className={`shrink-0 whitespace-nowrap ${p.type === 'income' ? 'text-emerald-700' : p.type === 'expense' ? 'text-red-700' : 'text-slate-600'}`}>
            {p.type === 'expense' ? '-' : p.type === 'income' ? '+' : ''}
            {formatCOP(p.amount)}
          </span>
        </li>
      ))}
    </ul>
  )
}
