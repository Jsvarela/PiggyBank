import { zodResolver } from '@hookform/resolvers/zod'
import { formatDate } from '../lib/format'
import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { api } from '../api/client'
import { useAccounts, useApiMutation, useCategories, useRecurring } from '../api/hooks'
import { FREQUENCIES, TX_TYPES, type Frequency, type RecurringBody, type RecurringRule, type TxType } from '../api/types'
import Loading from '../components/Loading'
import Ready from '../components/Ready'
import UpcomingList from '../components/UpcomingList'
import { todayBogota } from '../lib/dates'
import { formatCOP } from '../lib/money'

const schema = z
  .object({
    type: z.enum(['expense', 'income', 'transfer']),
    amount: z.number({ error: 'Ingresa un monto' }).int().positive('Debe ser mayor que 0'),
    account_id: z.number({ error: 'Elige una cuenta' }),
    to_account_id: z.number().nullable(),
    category_id: z.number().nullable(),
    description: z.string(),
    frequency: z.enum(['daily', 'weekly', 'biweekly', 'monthly', 'yearly']),
    start_date: z.string().min(1, 'Elige la fecha de inicio'),
    end_date: z.string(),
    active: z.boolean(),
  })
  .superRefine((v, ctx) => {
    if (v.type === 'transfer') {
      if (v.to_account_id === null) ctx.addIssue({ code: 'custom', path: ['to_account_id'], message: 'Elige la cuenta destino' })
      else if (v.to_account_id === v.account_id) ctx.addIssue({ code: 'custom', path: ['to_account_id'], message: 'Debe ser otra cuenta' })
    } else if (v.category_id === null) {
      ctx.addIssue({ code: 'custom', path: ['category_id'], message: 'Elige una categoría' })
    }
    if (v.end_date && v.end_date < v.start_date) ctx.addIssue({ code: 'custom', path: ['end_date'], message: 'Debe ser posterior al inicio' })
  })
type Values = z.infer<typeof schema>

const field = 'w-full rounded-lg border border-slate-300 p-2'
const num = (v: string) => (v ? Number(v) : null)

function RuleForm({ rule, onDone }: { rule?: RecurringRule; onDone: () => void }) {
  const qc = useQueryClient()
  const accounts = (useAccounts().data ?? []).filter((a) => !a.archived)
  const categories = useCategories().data ?? []
  const save = useApiMutation<RecurringBody>(rule ? 'PUT' : 'POST', () => (rule ? `/recurring/${rule.id}` : '/recurring'))
  const del = useApiMutation<number>('DELETE', (id) => `/recurring/${id}`)
  const { register, handleSubmit, watch, formState } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      type: rule?.type ?? 'expense',
      amount: rule?.amount,
      account_id: rule?.account_id ?? accounts[0]?.id,
      to_account_id: rule?.to_account_id ?? null,
      category_id: rule?.category_id ?? null,
      description: rule?.description ?? '',
      frequency: rule?.frequency ?? 'monthly',
      start_date: rule?.start_date ?? todayBogota(),
      end_date: rule?.end_date ?? '',
      active: rule?.active ?? true,
    },
  })
  const type = watch('type')
  const { errors } = formState
  const idField = { setValueAs: num }

  const onSubmit = handleSubmit((v) => {
    const body: RecurringBody = {
      ...v,
      to_account_id: v.type === 'transfer' ? v.to_account_id : null,
      category_id: v.type === 'transfer' ? null : v.category_id,
      description: v.description.trim() || null,
      end_date: v.end_date || null,
    }
    save.mutate(body, {
      // al crear una regla con fecha pasada, se ponen al día los movimientos de inmediato
      onSuccess: async () => {
        await api('/sync', { method: 'POST' })
        await qc.invalidateQueries()
        onDone()
      },
    })
  })

  return (
    <form onSubmit={onSubmit} className="space-y-2 rounded-xl bg-surface p-4 shadow-sm">
      <select aria-label="Tipo" className={field} {...register('type')}>
        {(Object.keys(TX_TYPES) as TxType[]).map((t) => (
          <option key={t} value={t}>
            {TX_TYPES[t]}
          </option>
        ))}
      </select>
      <input type="number" inputMode="numeric" placeholder="Monto en COP" className={field} {...register('amount', { valueAsNumber: true })} />
      {errors.amount && <p className="text-sm text-red-600">{errors.amount.message}</p>}
      <select aria-label={type === 'transfer' ? 'Desde' : 'Cuenta'} className={field} {...register('account_id', { valueAsNumber: true })}>
        {accounts.map((a) => (
          <option key={a.id} value={a.id}>
            {type === 'transfer' ? 'Desde: ' : ''}
            {a.name}
          </option>
        ))}
      </select>
      {type === 'transfer' ? (
        <>
          <select aria-label="Hacia" className={field} {...register('to_account_id', idField)}>
            <option value="">Hacia…</option>
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
          {errors.to_account_id && <p className="text-sm text-red-600">{errors.to_account_id.message}</p>}
        </>
      ) : (
        <>
          <select aria-label="Categoría" className={field} {...register('category_id', idField)}>
            <option value="">Categoría…</option>
            {categories
              .filter((c) => !c.archived && c.kind === type)
              .map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
          </select>
          {errors.category_id && <p className="text-sm text-red-600">{errors.category_id.message}</p>}
        </>
      )}
      <input placeholder="Descripción (Arriendo, Netflix…)" className={field} {...register('description')} />
      <select aria-label="Frecuencia" className={field} {...register('frequency')}>
        {(Object.keys(FREQUENCIES) as Frequency[]).map((f) => (
          <option key={f} value={f}>
            {FREQUENCIES[f]}
          </option>
        ))}
      </select>
      <div className="grid grid-cols-2 gap-2">
        <label className="text-sm text-slate-600">
          Inicia
          <input type="date" className={field} {...register('start_date')} />
        </label>
        <label className="text-sm text-slate-600">
          Termina (opcional)
          <input type="date" className={field} {...register('end_date')} />
        </label>
      </div>
      {errors.end_date && <p className="text-sm text-red-600">{errors.end_date.message}</p>}
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" {...register('active')} /> Activa
      </label>
      {(save.error || del.error) && <p className="text-sm text-red-600">{(save.error ?? del.error)?.message}</p>}
      <div className="flex gap-2">
        <button type="button" className="rounded-lg border px-4 py-2" onClick={onDone}>
          Cancelar
        </button>
        {rule && (
          <button type="button" className="rounded-lg border border-red-300 px-4 py-2 text-red-700" onClick={() => confirm('¿Borrar la regla? Los movimientos ya creados se conservan.') && del.mutate(rule.id, { onSuccess: onDone })}>
            Borrar
          </button>
        )}
        <button disabled={save.isPending} className="flex-1 rounded-lg bg-brand py-2 text-white disabled:opacity-60">
          Guardar
        </button>
      </div>
    </form>
  )
}

export default function Recurring() {
  const rulesQuery = useRecurring()
  const rules = rulesQuery.data ?? []
  const accounts = useAccounts()
  const categories = useCategories()
  // undefined = cerrado, null = nueva, RecurringRule = editar
  const [editing, setEditing] = useState<RecurringRule | null | undefined>(undefined)

  if (editing !== undefined)
    return (
      <Ready of={[accounts, categories]}>
        <RuleForm key={editing?.id ?? 'new'} rule={editing ?? undefined} onDone={() => setEditing(undefined)} />
      </Ready>
    )
  return (
    <div className="space-y-4">
      <button className="w-full rounded-lg bg-brand py-2 text-white" onClick={() => setEditing(null)}>
        Nueva regla recurrente
      </button>

      <section className="rounded-xl bg-surface p-4 shadow-sm">
        <h2 className="mb-2 font-medium">Próximos 30 días</h2>
        <UpcomingList />
      </section>

      <section className="rounded-xl bg-surface p-4 shadow-sm">
        <h2 className="mb-2 font-medium">Reglas</h2>
        {rulesQuery.isLoading && <Loading />}
        {!rulesQuery.isLoading && rules.length === 0 && (
          <p className="text-sm text-slate-500">Aún no tienes reglas. Agrega lo que se repite (arriendo, Netflix, salario…) y la app lo registra sola cada vez.</p>
        )}
        <ul className="divide-y">
          {rules.map((r) => (
            <li key={r.id}>
              <button className="flex w-full justify-between py-2 text-left" onClick={() => setEditing(r)}>
                <span>
                  <span className="block">{r.description || TX_TYPES[r.type]}</span>
                  <span className="block text-xs text-slate-500">
                    {FREQUENCIES[r.frequency]} · próxima {formatDate(r.next_run_date)}
                    {!r.active && ' · pausada'}
                  </span>
                </span>
                <span>{formatCOP(r.amount)}</span>
              </button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
