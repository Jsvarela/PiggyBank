import { useAccounts, useCategories } from '../api/hooks'
import { formatDate } from '../lib/format'
import type { Transaction } from '../api/types'
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
      <button className="flex w-full items-center justify-between py-2 text-left" onClick={() => open(tx)}>
        <span>
          <span className="block">{title}</span>
          <span className="block text-xs text-slate-500">
            {formatDate(tx.date)} · {sub}
          </span>
        </span>
        <span className={color}>
          {tx.type === 'expense' ? '-' : tx.type === 'income' ? '+' : ''}
          {formatCOP(tx.amount)}
        </span>
      </button>
    </li>
  )
}
