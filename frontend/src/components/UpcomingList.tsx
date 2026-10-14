import { useAccounts, useCategories, useUpcoming } from '../api/hooks'
import { formatDate } from '../lib/format'
import { formatCOP } from '../lib/money'

/** Próximos pagos de las reglas recurrentes (los siguientes 30 días). */
export default function UpcomingList({ limit }: { limit?: number }) {
  const { data = [] } = useUpcoming(30)
  const accounts = useAccounts().data ?? []
  const categories = useCategories().data ?? []
  const items = limit ? data.slice(0, limit) : data
  if (items.length === 0) return <p className="text-sm text-slate-500">Sin pagos programados en los próximos 30 días.</p>

  return (
    <ul className="divide-y">
      {items.map((p) => (
        <li key={`${p.rule_id}-${p.date}`} className="flex items-center justify-between py-2">
          <span>
            <span className="block">
              {p.description || categories.find((c) => c.id === p.category_id)?.name || 'Transferencia'}
            </span>
            <span className="block text-xs text-slate-500">
              {formatDate(p.date)} · {accounts.find((a) => a.id === p.account_id)?.name}
            </span>
          </span>
          <span className={p.type === 'income' ? 'text-emerald-700' : p.type === 'expense' ? 'text-red-700' : 'text-slate-600'}>
            {p.type === 'expense' ? '-' : p.type === 'income' ? '+' : ''}
            {formatCOP(p.amount)}
          </span>
        </li>
      ))}
    </ul>
  )
}
