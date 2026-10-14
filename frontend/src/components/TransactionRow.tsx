import { useAccounts, useCategories } from '../api/hooks'
import type { Transaction } from '../api/types'
import { formatDate } from '../lib/format'
import { formatCOP } from '../lib/money'
import { useEditor } from './editor'

export default function TransactionRow({ tx }: { tx: Transaction }) {
  const open = useEditor()
  const accounts = useAccounts().data ?? []
  const categories = useCategories().data ?? []
  const name = (id: number | null) => accounts.find((a) => a.id === id)?.name ?? '?'
  const title =
    tx.description || (tx.type === 'transfer' ? 'Transferencia' : categories.find((c) => c.id === tx.category_id)?.name)
  const sub =
    tx.type === 'transfer' ? `${name(tx.account_id)} → ${name(tx.to_account_id)}` : name(tx.account_id)
  const color = tx.type === 'income' ? 'text-emerald-700' : tx.type === 'expense' ? 'text-red-700' : 'text-slate-600'

  return (
    <li>
      {/* El texto puede ser larguísimo o no tener espacios (una referencia bancaria): se corta en 2 líneas
          y el monto nunca cede ni se sale de la pantalla. El texto completo se ve al abrir el movimiento. */}
      <button className="flex w-full items-start justify-between gap-3 py-2 text-left" onClick={() => open(tx)}>
        <span className="min-w-0">
          <span className="line-clamp-2 [overflow-wrap:anywhere]">{title}</span>
          <span className="line-clamp-2 text-xs text-slate-500 [overflow-wrap:anywhere]">
            {formatDate(tx.date)} · {sub}
          </span>
        </span>
        <span className={`shrink-0 whitespace-nowrap ${color}`}>
          {tx.type === 'expense' ? '-' : tx.type === 'income' ? '+' : ''}
          {formatCOP(tx.amount)}
        </span>
      </button>
    </li>
  )
}
