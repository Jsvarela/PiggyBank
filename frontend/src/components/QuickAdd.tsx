import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { api } from '../api/client'
import { useAccounts, useApiMutation, useCategories } from '../api/hooks'
import { TX_TYPES, type Transaction, type TransactionBody, type TxType } from '../api/types'
import { todayBogota } from '../lib/dates'
import { createTransaction } from '../lib/offlineQueue'

const LAST_ACCOUNT = 'lastAccountId'

const schema = z
  .object({
    type: z.enum(['expense', 'income', 'transfer']),
    amount: z.number({ error: 'Ingresa un monto' }).int().positive('Debe ser mayor que 0'),
    date: z.string().min(1, 'Elige una fecha'),
    account_id: z.number({ error: 'Elige una cuenta' }),
    to_account_id: z.number().nullable(),
    category_id: z.number().nullable(),
    description: z.string(),
  })
  .superRefine((v, ctx) => {
    if (v.type === 'transfer') {
      if (v.to_account_id === null) ctx.addIssue({ code: 'custom', path: ['to_account_id'], message: 'Elige la cuenta destino' })
      else if (v.to_account_id === v.account_id)
        ctx.addIssue({ code: 'custom', path: ['to_account_id'], message: 'Debe ser otra cuenta' })
    } else if (v.category_id === null) {
      ctx.addIssue({ code: 'custom', path: ['category_id'], message: 'Elige una categoría' })
    }
  })
type FormValues = z.infer<typeof schema>

function lastAccount(): number | undefined {
  try {
    const v = Number(localStorage.getItem(LAST_ACCOUNT))
    return v || undefined
  } catch {
    return undefined
  }
}

const chip = (on: boolean) =>
  `rounded-full border px-3 py-1.5 text-sm ${on ? 'border-emerald-600 bg-emerald-600 text-white' : 'border-slate-300 bg-surface'}`

export default function QuickAdd({ tx, onClose }: { tx?: Transaction; onClose: () => void }) {
  const accounts = (useAccounts().data ?? []).filter((a) => !a.archived)
  const categories = useCategories().data ?? []
  const qc = useQueryClient()
  // crear puede quedar en cola si no hay conexión; editar y borrar siempre necesitan red
  const save = useMutation({
    mutationFn: (body: TransactionBody) => (tx ? api(`/transactions/${tx.id}`, { method: 'PUT', body }) : createTransaction(body)),
    // sin `return`: no esperar el refresco, que sin conexión tarda en fallar y retrasaría cerrar la hoja
    onSuccess: () => {
      qc.invalidateQueries()
    },
  })
  const del = useApiMutation<string>('DELETE', (id) => `/transactions/${id}`)

  const { register, handleSubmit, watch, setValue, formState } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      type: tx?.type ?? 'expense',
      amount: tx?.amount,
      date: tx?.date ?? todayBogota(),
      account_id: tx?.account_id ?? lastAccount() ?? accounts[0]?.id,
      to_account_id: tx?.to_account_id ?? null,
      category_id: tx?.category_id ?? null,
      description: tx?.description ?? '',
    },
  })
  const type = watch('type')
  const accountId = watch('account_id')
  const toId = watch('to_account_id')
  const categoryId = watch('category_id')
  const { errors } = formState

  const pick = (name: 'account_id' | 'to_account_id' | 'category_id', v: number) =>
    setValue(name, v, { shouldValidate: formState.isSubmitted })
  const kindCategories = categories.filter((c) => !c.archived && c.kind === type)

  const onSubmit = handleSubmit((v) => {
    const body: TransactionBody = {
      ...v,
      to_account_id: v.type === 'transfer' ? v.to_account_id : null,
      category_id: v.type === 'transfer' ? null : v.category_id,
      description: v.description.trim() || null,
    }
    save.mutate(body, {
      onSuccess: () => {
        try {
          localStorage.setItem(LAST_ACCOUNT, String(v.account_id))
        } catch {
          /* sin almacenamiento: no pasa nada */
        }
        onClose()
      },
    })
  })

  return (
    <div className="fixed inset-0 z-20 flex items-end bg-black/40 sm:items-center sm:justify-center" onClick={onClose}>
      <form
        onSubmit={onSubmit}
        onClick={(e) => e.stopPropagation()}
        className="max-h-[92vh] w-full space-y-4 overflow-y-auto rounded-t-2xl bg-surface p-4 sm:max-w-md sm:rounded-2xl"
      >
        <div className="flex gap-2">
          {(Object.keys(TX_TYPES) as TxType[]).map((t) => (
            <button
              type="button"
              key={t}
              className={`flex-1 ${chip(type === t)}`}
              onClick={() => {
                setValue('type', t)
                setValue('category_id', null)
              }}
            >
              {TX_TYPES[t]}
            </button>
          ))}
        </div>

        <div>
          <input
            type="number"
            inputMode="numeric"
            autoFocus
            placeholder="Monto en COP"
            className="w-full rounded-lg border border-slate-300 p-3 text-2xl"
            {...register('amount', { valueAsNumber: true })}
          />
          {errors.amount && <p className="text-sm text-red-600">{errors.amount.message}</p>}
        </div>

        {type !== 'transfer' && (
          <div>
            <p className="mb-1 text-sm text-slate-600">Categoría</p>
            <div className="flex flex-wrap gap-2">
              {kindCategories.map((c) => (
                <button type="button" key={c.id} className={chip(categoryId === c.id)} onClick={() => pick('category_id', c.id)}>
                  {c.name}
                </button>
              ))}
            </div>
            {errors.category_id && <p className="text-sm text-red-600">{errors.category_id.message}</p>}
          </div>
        )}

        <div>
          <p className="mb-1 text-sm text-slate-600">{type === 'transfer' ? 'Desde' : 'Cuenta'}</p>
          <div className="flex flex-wrap gap-2">
            {accounts.map((a) => (
              <button type="button" key={a.id} className={chip(accountId === a.id)} onClick={() => pick('account_id', a.id)}>
                {a.name}
              </button>
            ))}
          </div>
          {errors.account_id && <p className="text-sm text-red-600">{errors.account_id.message}</p>}
        </div>

        {type === 'transfer' && (
          <div>
            <p className="mb-1 text-sm text-slate-600">Hacia</p>
            <div className="flex flex-wrap gap-2">
              {accounts.map((a) => (
                <button type="button" key={a.id} className={chip(toId === a.id)} onClick={() => pick('to_account_id', a.id)}>
                  {a.name}
                </button>
              ))}
            </div>
            {errors.to_account_id && <p className="text-sm text-red-600">{errors.to_account_id.message}</p>}
          </div>
        )}

        <div className="flex gap-2">
          <input type="date" className="rounded-lg border border-slate-300 p-2" {...register('date')} />
          <input placeholder="Descripción (opcional)" className="min-w-0 flex-1 rounded-lg border border-slate-300 p-2" {...register('description')} />
        </div>

        {(save.error || del.error) && <p className="text-sm text-red-600">{(save.error ?? del.error)?.message}</p>}

        <div className="flex gap-2">
          {tx && (
            <button
              type="button"
              className="rounded-lg border border-red-300 px-4 py-3 text-red-700"
              onClick={() => confirm('¿Borrar este movimiento?') && del.mutate(tx.id, { onSuccess: onClose })}
            >
              Borrar
            </button>
          )}
          <button type="submit" disabled={save.isPending} className="flex-1 rounded-lg bg-emerald-600 py-3 font-medium text-white disabled:opacity-60">
            {save.isPending ? 'Guardando…' : 'Guardar'}
          </button>
        </div>
      </form>
    </div>
  )
}
