import { zodResolver } from '@hookform/resolvers/zod'
import { formatMonth, formatPercent, plural } from '../lib/format'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { useApiMutation, useBudgetStatus, useCategories, useMonthlyReport } from '../api/hooks'
import type { BudgetBody, BudgetStatus } from '../api/types'
import Loading from '../components/Loading'
import { todayBogota } from '../lib/dates'
import { MAX_MONEY, MONEY_TOO_BIG, formatCOP } from '../lib/money'

const schema = z.object({
  category_id: z.number({ error: 'Elige una categoría' }),
  limit_amount: z.number({ error: 'Ingresa un monto' }).int().positive('Debe ser mayor que 0').max(MAX_MONEY, MONEY_TOO_BIG),
  alert_threshold: z.number().int().min(1).max(100),
  repeat: z.boolean(),
})
type Values = z.infer<typeof schema>

function shiftMonth(month: string, delta: number): string {
  const [y, m] = month.split('-').map(Number)
  const d = new Date(Date.UTC(y, m - 1 + delta, 1))
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}`
}

const BAR = { ok: 'bg-emerald-500', warning: 'bg-amber-500', exceeded: 'bg-red-600' }

function BudgetForm({ month, item, onDone }: { month: string; item?: BudgetStatus; onDone: () => void }) {
  const categories = (useCategories().data ?? []).filter((c) => c.kind === 'expense' && !c.archived)
  const save = useApiMutation<BudgetBody>('PUT', () => '/budgets')
  const del = useApiMutation<number>('DELETE', (id) => `/budgets/${id}`)
  const { register, handleSubmit, formState } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      category_id: item?.category_id,
      limit_amount: item?.limit,
      alert_threshold: item?.alert_threshold ?? 80,
      repeat: item?.is_default ?? true,
    },
  })
  const { errors } = formState

  return (
    <form
      onSubmit={handleSubmit(({ repeat, ...v }) => save.mutate({ ...v, month: repeat ? null : month }, { onSuccess: onDone }))}
      className="space-y-2 rounded-xl bg-surface p-4 shadow-sm"
    >
      {item ? (
        <p className="text-lg font-medium">{item.category_name}</p>
      ) : (
        <select className="w-full rounded-lg border border-slate-300 p-2" {...register('category_id', { setValueAs: (v) => (v ? Number(v) : undefined) })}>
          <option value="">Categoría…</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.parent_id ? '↳ ' : ''}
              {c.name}
            </option>
          ))}
        </select>
      )}
      {errors.category_id && <p className="text-sm text-red-600">{errors.category_id.message}</p>}
      <input type="number" inputMode="numeric" placeholder="Límite mensual en COP" className="w-full rounded-lg border border-slate-300 p-2" {...register('limit_amount', { valueAsNumber: true })} />
      {errors.limit_amount && <p className="text-sm text-red-600">{errors.limit_amount.message}</p>}
      <label className="block text-sm text-slate-600">
        Avisar al llegar a (%)
        <input type="number" inputMode="numeric" className="mt-1 w-full rounded-lg border border-slate-300 p-2" {...register('alert_threshold', { valueAsNumber: true })} />
      </label>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" {...register('repeat')} /> Repetir cada mes (si no, solo {formatMonth(month)})
      </label>
      {(save.error || del.error) && <p className="text-sm text-red-600">{(save.error ?? del.error)?.message}</p>}
      <div className="flex gap-2">
        <button type="button" className="rounded-lg border px-4 py-2" onClick={onDone}>
          Cancelar
        </button>
        {item && (
          <button type="button" className="rounded-lg border border-red-300 px-4 py-2 text-red-700" onClick={() => confirm('¿Quitar este presupuesto?') && del.mutate(item.budget_id, { onSuccess: onDone })}>
            Quitar
          </button>
        )}
        <button className="flex-1 rounded-lg bg-brand py-2 text-white">Guardar</button>
      </div>
    </form>
  )
}

export default function Budgets() {
  const [month, setMonth] = useState(todayBogota().slice(0, 7))
  const statusQuery = useBudgetStatus(month)
  const status = statusQuery.data ?? []
  const report = useMonthlyReport(month).data
  // undefined = cerrado, null = nuevo, BudgetStatus = editar
  const [editing, setEditing] = useState<BudgetStatus | null | undefined>(undefined)

  if (editing !== undefined) return <BudgetForm key={editing?.budget_id ?? 'new'} month={month} item={editing ?? undefined} onDone={() => setEditing(undefined)} />

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <button className="rounded-lg border px-3 py-1" aria-label="Mes anterior" onClick={() => setMonth(shiftMonth(month, -1))}>
          ‹
        </button>
        <span className="font-medium">{formatMonth(month)}</span>
        <button className="rounded-lg border px-3 py-1" aria-label="Mes siguiente" onClick={() => setMonth(shiftMonth(month, 1))}>
          ›
        </button>
      </div>

      <button className="w-full rounded-lg bg-brand py-2 text-white" onClick={() => setEditing(null)}>
        Nuevo presupuesto
      </button>

      <section className="space-y-3">
        {statusQuery.isLoading && <Loading />}
        {!statusQuery.isLoading && status.length === 0 && (
          <p className="text-sm text-slate-500">Sin presupuestos para este mes. Toca «Nuevo presupuesto» para ponerle un tope a una categoría (por ejemplo, Comida) y recibir avisos al acercarte.</p>
        )}
        {status.map((b) => (
          <button key={b.budget_id} className="block w-full rounded-xl bg-surface p-3 text-left shadow-sm" onClick={() => setEditing(b)}>
            {/* nombre y montos comparten la fila; si no caben, los montos pasan a la línea de abajo (y solo se parten en el "/") */}
            <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
              <span className="min-w-0 grow basis-40 [overflow-wrap:anywhere]">{b.category_name}</span>
              <span className="text-sm text-slate-600">
                <span className="whitespace-nowrap">{formatCOP(b.spent)}</span> / <span className="whitespace-nowrap">{formatCOP(b.limit)}</span>
              </span>
            </div>
            <div className="my-2 h-2 rounded bg-slate-200">
              <div className={`h-2 rounded ${BAR[b.alert]}`} style={{ width: `${Math.min(b.percent, 100)}%` }} />
            </div>
            <p className={`text-xs ${b.alert === 'exceeded' ? 'text-red-700' : 'text-slate-500'}`}>
              {formatPercent(b.percent)} · {b.remaining >= 0 ? `quedan ${formatCOP(b.remaining)}` : `te pasaste ${formatCOP(-b.remaining)}`} · {plural(b.days_left, 'día restante', 'días restantes')}
              {b.is_default && ' · se repite cada mes'}
            </p>
          </button>
        ))}
      </section>

      {report && (
        <section className="rounded-xl bg-surface p-4 shadow-sm">
          <h2 className="mb-1 font-medium">Resumen del mes</h2>
          <p className="mb-2 text-sm text-slate-600">
            Gastos {formatCOP(report.expense)} (mes anterior {formatCOP(report.previous_expense)}) · Ingresos {formatCOP(report.income)}
          </p>
          {report.categories.length === 0 && <p className="text-sm text-slate-500">Sin gastos.</p>}
          <ul className="divide-y">
            {report.categories.map((c) => (
              <li key={c.category_id} className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5 py-2 text-sm">
                <span className="min-w-0 grow basis-32 [overflow-wrap:anywhere]">{c.name}</span>
                <span className="text-right">
                  <span className="whitespace-nowrap">{formatCOP(c.amount)}</span>{' '}
                  <span className={`whitespace-nowrap ${c.diff > 0 ? 'text-red-700' : c.diff < 0 ? 'text-emerald-700' : 'text-slate-500'}`}>
                    ({c.diff > 0 ? '+' : ''}
                    {formatCOP(c.diff)})
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
