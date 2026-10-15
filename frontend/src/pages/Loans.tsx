import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { useApiMutation, useLoans } from '../api/hooks'
import type { Loan, LoanBody } from '../api/types'
import Loading from '../components/Loading'
import { todayBogota } from '../lib/dates'
import { formatDate } from '../lib/format'
import { MAX_MONEY, MONEY_TOO_BIG, formatCOP } from '../lib/money'

const money = z.number({ error: 'Ingresa un monto' }).int().positive('Debe ser mayor que 0').max(MAX_MONEY, MONEY_TOO_BIG)
const schema = z.object({
  person: z.string().trim().min(1, 'Escribe el nombre de la persona'),
  amount: money,
  expected_amount: money,
  due_date: z.string(),
  note: z.string(),
})
type Values = z.infer<typeof schema>

const field = 'w-full rounded-lg border border-slate-300 p-2'

function LoanForm({ loan, onDone }: { loan?: Loan; onDone: () => void }) {
  const save = useApiMutation<LoanBody>(loan ? 'PUT' : 'POST', () => (loan ? `/loans/${loan.id}` : '/loans'))
  const del = useApiMutation<number>('DELETE', (id) => `/loans/${id}`)
  const { register, handleSubmit, formState, setValue } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      person: loan?.person ?? '',
      amount: loan?.amount,
      expected_amount: loan?.expected_amount,
      due_date: loan?.due_date ?? '',
      note: loan?.note ?? '',
    },
  })
  const { errors } = formState

  return (
    <form
      onSubmit={handleSubmit((v) => save.mutate({ ...v, due_date: v.due_date || null, note: v.note.trim() || null, paid: loan?.paid ?? false }, { onSuccess: onDone }))}
      className="space-y-2 rounded-xl bg-surface p-4 shadow-sm"
    >
      <input placeholder="¿A quién le prestaste?" className={field} {...register('person')} />
      {errors.person && <p className="text-sm text-red-600">{errors.person.message}</p>}
      <input
        type="number"
        inputMode="numeric"
        placeholder="Cuánto prestaste (COP)"
        className={field}
        {...register('amount', {
          valueAsNumber: true,
          // lo más común es recibir lo mismo que se prestó: se copia mientras no hayas tocado el otro campo
          onChange: (e) => {
            if (!formState.dirtyFields.expected_amount) setValue('expected_amount', e.target.valueAsNumber)
          },
        })}
      />
      {errors.amount && <p className="text-sm text-red-600">{errors.amount.message}</p>}
      <input
        type="number"
        inputMode="numeric"
        placeholder="Cuánto esperas recibir (COP)"
        className={field}
        {...register('expected_amount', { valueAsNumber: true })}
      />
      {errors.expected_amount && <p className="text-sm text-red-600">{errors.expected_amount.message}</p>}
      <label className="block text-sm text-slate-600">
        Fecha estimada de pago (opcional)
        <input type="date" className={field} {...register('due_date')} />
      </label>
      <input placeholder="Nota (opcional)" className={field} {...register('note')} />
      {(save.error || del.error) && <p className="text-sm text-red-600">{(save.error ?? del.error)?.message}</p>}
      <div className="flex gap-2">
        <button type="button" className="rounded-lg border px-4 py-2" onClick={onDone}>
          Cancelar
        </button>
        {loan && (
          <button
            type="button"
            className="rounded-lg border border-red-300 px-4 py-2 text-red-700"
            onClick={() => confirm('¿Borrar este préstamo?') && del.mutate(loan.id, { onSuccess: onDone })}
          >
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

export default function Loans() {
  const q = useLoans()
  const loans = q.data ?? []
  const toggle = useApiMutation<Loan>('PUT', (l) => `/loans/${l.id}`)
  // undefined = cerrado, null = nuevo, Loan = editar
  const [editing, setEditing] = useState<Loan | null | undefined>(undefined)
  const today = todayBogota()

  if (editing !== undefined) return <LoanForm key={editing?.id ?? 'new'} loan={editing ?? undefined} onDone={() => setEditing(undefined)} />

  const pending = loans.filter((l) => !l.paid)
  return (
    <div className="space-y-3">
      <button className="w-full rounded-lg bg-brand py-2 text-white" onClick={() => setEditing(null)}>
        Nuevo préstamo
      </button>
      {q.isLoading && <Loading />}
      {pending.length > 0 && (
        <section className="grid grid-cols-2 gap-2 text-center">
          <div className="rounded-xl bg-surface p-3 shadow-sm">
            <p className="text-xs text-slate-500">Prestado sin cobrar</p>
            <p className="font-semibold">{formatCOP(pending.reduce((s, l) => s + l.amount, 0))}</p>
          </div>
          <div className="rounded-xl bg-surface p-3 shadow-sm">
            <p className="text-xs text-slate-500">Esperas recibir</p>
            <p className="font-semibold">{formatCOP(pending.reduce((s, l) => s + l.expected_amount, 0))}</p>
          </div>
        </section>
      )}
      {!q.isLoading && loans.length === 0 && (
        <p className="text-sm text-slate-500">Aquí anotas el dinero que le prestaste a alguien, cuánto esperas recibir y para cuándo. No cambia los saldos de tus cuentas.</p>
      )}
      {loans.map((l) => {
        const late = !l.paid && l.due_date !== null && l.due_date < today
        return (
          <section key={l.id} className={`rounded-xl bg-surface p-4 shadow-sm ${l.paid ? 'opacity-60' : ''}`}>
            <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
              <span className="flex min-w-0 grow basis-40 items-baseline gap-2">
                <span className="min-w-0 font-medium [overflow-wrap:anywhere]">{l.person}</span>
                <button className="shrink-0 text-xs text-slate-600 underline" onClick={() => setEditing(l)}>
                  Editar
                </button>
              </span>
              <span className="whitespace-nowrap text-sm text-slate-600">{formatCOP(l.expected_amount)}</span>
            </div>
            <p className="text-xs text-slate-500">
              Prestaste {formatCOP(l.amount)}
              {l.due_date && ` · pago estimado ${formatDate(l.due_date)}`}
              {l.note && ` · ${l.note}`}
            </p>
            {late && <p className="text-xs text-red-700">Vencido</p>}
            <button
              className="mt-2 rounded-lg border border-brand px-3 py-1 text-sm text-emerald-700"
              disabled={toggle.isPending}
              onClick={() => toggle.mutate({ ...l, paid: !l.paid })}
            >
              {l.paid ? 'Marcar como pendiente' : 'Ya me pagó'}
            </button>
          </section>
        )
      })}
    </div>
  )
}
