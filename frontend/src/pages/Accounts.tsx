import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { useAccounts, useApiMutation } from '../api/hooks'
import { ACCOUNT_TYPES, type Account, type AccountBody, type AccountType } from '../api/types'
import Loading from '../components/Loading'
import { MAX_MONEY, MONEY_TOO_BIG, formatCOP } from '../lib/money'

const schema = z.object({
  name: z.string().trim().min(1, 'Escribe un nombre'),
  type: z.enum(['cash', 'bank', 'digital_wallet', 'credit_card', 'savings']),
  initial_balance: z.number({ error: 'Ingresa un número' }).int('Sin decimales').min(-MAX_MONEY, MONEY_TOO_BIG).max(MAX_MONEY, MONEY_TOO_BIG),
  archived: z.boolean(),
})

function AccountForm({ account, onDone }: { account?: Account; onDone: () => void }) {
  const save = useApiMutation<AccountBody>(account ? 'PUT' : 'POST', () => (account ? `/accounts/${account.id}` : '/accounts'))
  const del = useApiMutation<number>('DELETE', (id) => `/accounts/${id}`)
  const { register, handleSubmit, formState } = useForm<AccountBody>({
    resolver: zodResolver(schema),
    defaultValues: account ?? { name: '', type: 'bank', initial_balance: 0, archived: false },
  })
  const { errors } = formState

  return (
    <form onSubmit={handleSubmit((v) => save.mutate(v, { onSuccess: onDone }))} className="space-y-2 rounded-xl bg-surface p-4 shadow-sm">
      <input placeholder="Nombre (Nequi, Bancolombia…)" className="w-full rounded-lg border border-slate-300 p-2" {...register('name')} />
      {errors.name && <p className="text-sm text-red-600">{errors.name.message}</p>}
      <select className="w-full rounded-lg border border-slate-300 p-2" {...register('type')}>
        {(Object.keys(ACCOUNT_TYPES) as AccountType[]).map((t) => (
          <option key={t} value={t}>
            {ACCOUNT_TYPES[t]}
          </option>
        ))}
      </select>
      <label className="block text-sm text-slate-600">
        Saldo inicial (en tarjetas de crédito, la deuda va en negativo)
        <input type="number" inputMode="numeric" className="mt-1 w-full rounded-lg border border-slate-300 p-2" {...register('initial_balance', { valueAsNumber: true })} />
      </label>
      {errors.initial_balance && <p className="text-sm text-red-600">{errors.initial_balance.message}</p>}
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" {...register('archived')} /> Archivada
      </label>
      {(save.error || del.error) && <p className="text-sm text-red-600">{(save.error ?? del.error)?.message}</p>}
      <div className="flex gap-2">
        <button type="button" className="rounded-lg border px-4 py-2" onClick={onDone}>
          Cancelar
        </button>
        {account && (
          <button type="button" className="rounded-lg border border-red-300 px-4 py-2 text-red-700" onClick={() => confirm('¿Borrar la cuenta?') && del.mutate(account.id, { onSuccess: onDone })}>
            Borrar
          </button>
        )}
        <button className="flex-1 rounded-lg bg-brand py-2 text-white">Guardar</button>
      </div>
    </form>
  )
}

export default function Accounts() {
  const query = useAccounts()
  const accounts = query.data ?? []
  // undefined = cerrado, null = nueva, Account = editar
  const [editing, setEditing] = useState<Account | null | undefined>(undefined)

  if (editing !== undefined) return <AccountForm key={editing?.id ?? 'new'} account={editing ?? undefined} onDone={() => setEditing(undefined)} />
  return (
    <div className="space-y-3">
      <button className="w-full rounded-lg bg-brand py-2 text-white" onClick={() => setEditing(null)}>
        Nueva cuenta
      </button>
      {query.isLoading && <Loading />}
      {!query.isLoading && accounts.length === 0 && (
        <p className="text-sm text-slate-500">Aún no tienes cuentas. Crea una por cada lugar donde guardas plata: efectivo, banco, Nequi, tarjeta…</p>
      )}
      <ul className="divide-y rounded-xl bg-surface px-4 shadow-sm">
        {accounts.map((a) => (
          <li key={a.id}>
            <button className="flex w-full items-start justify-between gap-3 py-3 text-left" onClick={() => setEditing(a)}>
              <span className="min-w-0 [overflow-wrap:anywhere]">
                {a.name} <span className="text-xs text-slate-500">{ACCOUNT_TYPES[a.type]}{a.archived && ' · archivada'}</span>
              </span>
              <span className={`shrink-0 whitespace-nowrap ${a.balance < 0 ? 'text-red-700' : ''}`}>{formatCOP(a.balance)}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
