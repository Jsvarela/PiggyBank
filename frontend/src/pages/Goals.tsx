import { zodResolver } from '@hookform/resolvers/zod'
import { formatDate } from '../lib/format'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { useAccounts, useApiMutation, useGoals } from '../api/hooks'
import type { Goal, GoalBody } from '../api/types'
import Loading from '../components/Loading'
import Ready from '../components/Ready'
import { formatCOP } from '../lib/money'

const schema = z.object({
  name: z.string().trim().min(1, 'Escribe un nombre'),
  target_amount: z.number({ error: 'Ingresa un monto' }).int().positive('Debe ser mayor que 0'),
  deadline: z.string(),
  account_id: z.number().nullable(),
})
type Values = z.infer<typeof schema>

const field = 'w-full rounded-lg border border-slate-300 p-2'

function GoalForm({ goal, onDone }: { goal?: Goal; onDone: () => void }) {
  const accounts = (useAccounts().data ?? []).filter((a) => !a.archived)
  const save = useApiMutation<GoalBody>(goal ? 'PUT' : 'POST', () => (goal ? `/savings-goals/${goal.id}` : '/savings-goals'))
  const del = useApiMutation<number>('DELETE', (id) => `/savings-goals/${id}`)
  const { register, handleSubmit, formState } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { name: goal?.name ?? '', target_amount: goal?.target_amount, deadline: goal?.deadline ?? '', account_id: goal?.account_id ?? null },
  })
  const { errors } = formState

  return (
    <form
      onSubmit={handleSubmit((v) => save.mutate({ ...v, deadline: v.deadline || null }, { onSuccess: onDone }))}
      className="space-y-2 rounded-xl bg-surface p-4 shadow-sm"
    >
      <input placeholder="Nombre de la meta (Viaje, Moto…)" className={field} {...register('name')} />
      {errors.name && <p className="text-sm text-red-600">{errors.name.message}</p>}
      <input type="number" inputMode="numeric" placeholder="Monto objetivo en COP" className={field} {...register('target_amount', { valueAsNumber: true })} />
      {errors.target_amount && <p className="text-sm text-red-600">{errors.target_amount.message}</p>}
      <label className="block text-sm text-slate-600">
        Fecha límite (opcional)
        <input type="date" className={field} {...register('deadline')} />
      </label>
      <label className="block text-sm text-slate-600">
        Cuenta donde se guarda (necesaria para aportar)
        <select className={field} {...register('account_id', { setValueAs: (v) => (v ? Number(v) : null) })}>
          <option value="">Sin cuenta</option>
          {accounts.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </select>
      </label>
      {(save.error || del.error) && <p className="text-sm text-red-600">{(save.error ?? del.error)?.message}</p>}
      <div className="flex gap-2">
        <button type="button" className="rounded-lg border px-4 py-2" onClick={onDone}>
          Cancelar
        </button>
        {goal && (
          <button type="button" className="rounded-lg border border-red-300 px-4 py-2 text-red-700" onClick={() => confirm('¿Borrar la meta? Los aportes ya hechos se conservan como transferencias.') && del.mutate(goal.id, { onSuccess: onDone })}>
            Borrar
          </button>
        )}
        <button className="flex-1 rounded-lg bg-brand py-2 text-white">Guardar</button>
      </div>
    </form>
  )
}

const contributeSchema = z.object({
  amount: z.number({ error: 'Ingresa un monto' }).int().positive('Debe ser mayor que 0'),
  from_account_id: z.number({ error: 'Elige una cuenta' }),
})
type ContributeValues = z.infer<typeof contributeSchema>

function ContributeForm({ goal, onDone }: { goal: Goal; onDone: () => void }) {
  const accounts = (useAccounts().data ?? []).filter((a) => !a.archived && a.id !== goal.account_id)
  const contribute = useApiMutation<ContributeValues>('POST', () => `/savings-goals/${goal.id}/contribute`)
  const { register, handleSubmit, formState } = useForm<ContributeValues>({
    resolver: zodResolver(contributeSchema),
    defaultValues: { from_account_id: accounts[0]?.id, amount: goal.monthly_suggested || undefined },
  })

  return (
    <form onSubmit={handleSubmit((v) => contribute.mutate(v, { onSuccess: onDone }))} className="mt-2 space-y-2 border-t pt-2">
      <input type="number" inputMode="numeric" autoFocus placeholder="Monto a aportar" className={field} {...register('amount', { valueAsNumber: true })} />
      {formState.errors.amount && <p className="text-sm text-red-600">{formState.errors.amount.message}</p>}
      <select aria-label="Desde la cuenta" className={field} {...register('from_account_id', { valueAsNumber: true })}>
        {accounts.map((a) => (
          <option key={a.id} value={a.id}>
            Desde: {a.name}
          </option>
        ))}
      </select>
      {formState.errors.from_account_id && <p className="text-sm text-red-600">{formState.errors.from_account_id.message}</p>}
      {contribute.error && <p className="text-sm text-red-600">{contribute.error.message}</p>}
      <div className="flex gap-2">
        <button type="button" className="rounded-lg border px-4 py-2" onClick={onDone}>
          Cancelar
        </button>
        <button className="flex-1 rounded-lg bg-brand py-2 text-white">Aportar</button>
      </div>
    </form>
  )
}

export default function Goals() {
  const goalsQuery = useGoals()
  const goals = goalsQuery.data ?? []
  const accounts = useAccounts()
  // undefined = cerrado, null = nueva, Goal = editar
  const [editing, setEditing] = useState<Goal | null | undefined>(undefined)
  const [contributing, setContributing] = useState<number | null>(null)

  if (editing !== undefined)
    return (
      <Ready of={[accounts]}>
        <GoalForm key={editing?.id ?? 'new'} goal={editing ?? undefined} onDone={() => setEditing(undefined)} />
      </Ready>
    )
  return (
    <div className="space-y-3">
      <button className="w-full rounded-lg bg-brand py-2 text-white" onClick={() => setEditing(null)}>
        Nueva meta
      </button>
      {goalsQuery.isLoading && <Loading />}
      {!goalsQuery.isLoading && goals.length === 0 && (
        <p className="text-sm text-slate-500">Aún no tienes metas de ahorro. Crea una (un viaje, un celular, un fondo de emergencia) y ve cuánto te falta.</p>
      )}
      {goals.map((g) => (
        <section key={g.id} className="rounded-xl bg-surface p-4 shadow-sm">
          <div className="flex justify-between">
            <span className="flex items-baseline gap-2">
              <span className="font-medium">{g.name}</span>
              <button className="text-xs text-slate-600 underline" onClick={() => setEditing(g)}>
                Editar
              </button>
            </span>
            <span className="text-sm text-slate-600">
              {formatCOP(g.saved)} / {formatCOP(g.target_amount)}
            </span>
          </div>
          <div className="my-2 h-2 rounded bg-slate-200">
            <div className={`h-2 rounded ${g.reached ? 'bg-brand' : 'bg-sky-500'}`} style={{ width: `${Math.min(g.percent, 100)}%` }} />
          </div>
          <p className="text-xs text-slate-500">
            {g.reached ? '¡Meta cumplida!' : `${g.percent}% · faltan ${formatCOP(g.remaining)}`}
            {!g.reached && g.monthly_suggested !== null && ` · sugerido ${formatCOP(g.monthly_suggested)} al mes`}
            {g.deadline && ` · hasta ${formatDate(g.deadline)}`}
          </p>
          {contributing === g.id ? (
            <Ready of={[accounts]}>
              <ContributeForm goal={g} onDone={() => setContributing(null)} />
            </Ready>
          ) : g.account_id === null ? (
            <p className="mt-2 text-xs text-amber-700">Asigna una cuenta de ahorro (editar la meta) para poder aportar.</p>
          ) : (
            <button className="mt-2 rounded-lg border border-brand px-3 py-1 text-sm text-emerald-700" onClick={() => setContributing(g.id)}>
              Aportar
            </button>
          )}
        </section>
      ))}
    </div>
  )
}
