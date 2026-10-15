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

type Direction = Loan['direction']

// Todo el texto que cambia entre «me deben» y «debo» vive aquí.
const TEXT = {
  lent: {
    tab: 'Me deben',
    person: '¿A quién le prestaste?',
    amount: 'Cuánto prestaste (COP)',
    expected: 'Cuánto esperas recibir (COP)',
    received: 'Ya recibido (opcional)',
    date: 'Fecha estimada de pago (opcional)',
    gave: 'Prestaste',
    pending: 'Falta por cobrar',
    done: 'Cobrado',
    all: 'Me pagó todo',
    empty: 'Aquí anotas el dinero que le prestaste a alguien, cuánto esperas recibir y para cuándo. No cambia los saldos de tus cuentas.',
  },
  borrowed: {
    tab: 'Debo',
    person: '¿A quién le debes?',
    amount: 'Cuánto te prestaron (COP)',
    expected: 'Cuánto debes devolver (COP)',
    received: 'Ya pagado (opcional)',
    date: 'Fecha límite de pago (opcional)',
    gave: 'Te prestaron',
    pending: 'Falta por pagar',
    done: 'Pagado',
    all: 'Pagué todo',
    empty: 'Aquí anotas lo que le debes a otras personas para no olvidarlo. No cambia los saldos de tus cuentas.',
  },
} as const

const money = z.number({ error: 'Ingresa un monto' }).int().positive('Debe ser mayor que 0').max(MAX_MONEY, MONEY_TOO_BIG)
const schema = z
  .object({
    person: z.string().trim().min(1, 'Escribe el nombre de la persona').max(100, 'Máximo 100 caracteres'),
    amount: money,
    expected_amount: money,
    // vacío = 0; el campo numérico vacío llega como NaN
    received: z.number().int().min(0, 'No puede ser negativo').max(MAX_MONEY, MONEY_TOO_BIG).or(z.nan()),
    due_date: z.string(),
    note: z.string().max(255, 'Máximo 255 caracteres'),
  })
  .refine((v) => Number.isNaN(v.received) || v.received <= v.expected_amount, { path: ['received'], message: 'No puede ser más que el total' })
type Values = z.infer<typeof schema>

const field = 'w-full rounded-lg border border-slate-300 p-2'

function LoanForm({ loan, direction, onDone }: { loan?: Loan; direction: Direction; onDone: () => void }) {
  const t = TEXT[direction]
  const save = useApiMutation<LoanBody>(loan ? 'PUT' : 'POST', () => (loan ? `/loans/${loan.id}` : '/loans'))
  const del = useApiMutation<number>('DELETE', (id) => `/loans/${id}`)
  const { register, handleSubmit, formState, setValue } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      person: loan?.person ?? '',
      amount: loan?.amount,
      expected_amount: loan?.expected_amount,
      received: loan?.received || undefined,
      due_date: loan?.due_date ?? '',
      note: loan?.note ?? '',
    },
  })
  const { errors } = formState

  return (
    <form
      onSubmit={handleSubmit((v) =>
        save.mutate({ ...v, received: Number.isNaN(v.received) ? 0 : v.received, direction, due_date: v.due_date || null, note: v.note.trim() || null }, { onSuccess: onDone }),
      )}
      className="space-y-2 rounded-xl bg-surface p-4 shadow-sm"
    >
      <input placeholder={t.person} className={field} {...register('person')} />
      {errors.person && <p className="text-sm text-red-600">{errors.person.message}</p>}
      <input
        type="number"
        inputMode="numeric"
        placeholder={t.amount}
        className={field}
        {...register('amount', {
          valueAsNumber: true,
          // lo más común es devolver lo mismo que se prestó: se copia mientras no hayas tocado el otro campo
          onChange: (e) => {
            if (!loan && !formState.dirtyFields.expected_amount) setValue('expected_amount', e.target.valueAsNumber)
          },
        })}
      />
      {errors.amount && <p className="text-sm text-red-600">{errors.amount.message}</p>}
      <input type="number" inputMode="numeric" placeholder={t.expected} className={field} {...register('expected_amount', { valueAsNumber: true })} />
      {errors.expected_amount && <p className="text-sm text-red-600">{errors.expected_amount.message}</p>}
      <input type="number" inputMode="numeric" placeholder={t.received} className={field} {...register('received', { valueAsNumber: true })} />
      {errors.received && <p className="text-sm text-red-600">{errors.received.message}</p>}
      <label className="block text-sm text-slate-600">
        {t.date}
        <input type="date" className={field} {...register('due_date')} />
      </label>
      <input placeholder="Nota (opcional)" className={field} {...register('note')} />
      {errors.note && <p className="text-sm text-red-600">{errors.note.message}</p>}
      {(save.error || del.error) && <p className="text-sm text-red-600">{(save.error ?? del.error)?.message}</p>}
      <div className="flex gap-2">
        <button type="button" className="rounded-lg border px-4 py-2" onClick={onDone}>
          Cancelar
        </button>
        {loan && (
          <button
            type="button"
            className="rounded-lg border border-red-300 px-4 py-2 text-red-700"
            onClick={() => confirm('¿Borrar este registro?') && del.mutate(loan.id, { onSuccess: onDone })}
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

/** Abono: un monto cualquiera hasta lo que falta, o todo lo que falta de una vez. */
function PaymentForm({ loan, onDone }: { loan: Loan; onDone: () => void }) {
  const left = loan.expected_amount - loan.received
  const pay = useApiMutation<{ id: number; amount: number }>('POST', (b) => `/loans/${b.id}/payments`)
  const [amount, setAmount] = useState('')
  const n = Number(amount)
  const bad = !Number.isInteger(n) || n <= 0 || n > left

  return (
    <div className="mt-2 space-y-2 border-t pt-2">
      <input
        type="number"
        inputMode="numeric"
        autoFocus
        value={amount}
        onChange={(e) => setAmount(e.target.value)}
        placeholder={`Monto del abono (máx. ${formatCOP(left)})`}
        className={field}
      />
      {amount !== '' && n > left && <p className="text-sm text-red-600">Solo faltan {formatCOP(left)}</p>}
      {pay.error && <p className="text-sm text-red-600">{pay.error.message}</p>}
      <div className="flex gap-2">
        <button type="button" className="rounded-lg border px-3 py-2" onClick={onDone}>
          Cancelar
        </button>
        <button type="button" disabled={bad || pay.isPending} className="flex-1 rounded-lg bg-brand py-2 text-white disabled:opacity-60" onClick={() => pay.mutate({ id: loan.id, amount: n }, { onSuccess: onDone })}>
          Abonar
        </button>
      </div>
    </div>
  )
}

export default function Loans() {
  const q = useLoans()
  const all = q.data ?? []
  const payAll = useApiMutation<{ id: number; amount: number }>('POST', (b) => `/loans/${b.id}/payments`)
  const [direction, setDirection] = useState<Direction>('lent')
  // undefined = cerrado, null = nuevo, Loan = editar
  const [editing, setEditing] = useState<Loan | null | undefined>(undefined)
  const [paying, setPaying] = useState<number | null>(null)
  const today = todayBogota()
  const t = TEXT[direction]

  if (editing !== undefined)
    return <LoanForm key={editing?.id ?? 'new'} loan={editing ?? undefined} direction={editing?.direction ?? direction} onDone={() => setEditing(undefined)} />

  const loans = all.filter((l) => l.direction === direction)
  const pending = loans.filter((l) => !l.paid)
  const tab = (d: Direction) =>
    `flex-1 rounded-full border px-3 py-1.5 text-sm ${direction === d ? 'border-brand bg-brand text-white' : 'border-slate-300 bg-surface'}`

  return (
    <div className="space-y-3">
      <div className="flex gap-2" role="group" aria-label="Tipo">
        {(['lent', 'borrowed'] as const).map((d) => (
          <button key={d} className={tab(d)} aria-pressed={direction === d} onClick={() => setDirection(d)}>
            {TEXT[d].tab}
          </button>
        ))}
      </div>
      <button className="w-full rounded-lg bg-brand py-2 text-white" onClick={() => setEditing(null)}>
        {direction === 'lent' ? 'Nuevo préstamo' : 'Nueva deuda'}
      </button>
      {q.isLoading && <Loading />}
      {pending.length > 0 && (
        <section className="rounded-xl bg-surface p-3 text-center shadow-sm">
          <p className="text-xs text-slate-500">{t.pending}</p>
          <p className="text-lg font-semibold [overflow-wrap:anywhere]">{formatCOP(pending.reduce((s, l) => s + l.expected_amount - l.received, 0))}</p>
        </section>
      )}
      {!q.isLoading && loans.length === 0 && <p className="text-sm text-slate-500">{t.empty}</p>}
      {loans.map((l) => {
        const late = !l.paid && l.due_date !== null && l.due_date < today
        const left = l.expected_amount - l.received
        return (
          <section key={l.id} className={`rounded-xl bg-surface p-4 ${l.paid ? 'border border-dashed border-slate-300' : 'shadow-sm'}`}>
            <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
              <span className="flex min-w-0 grow basis-40 items-baseline gap-2">
                <span className="min-w-0 font-medium [overflow-wrap:anywhere]">{l.person}</span>
                <button className="shrink-0 text-xs text-slate-600 underline" onClick={() => setEditing(l)}>
                  Editar
                </button>
              </span>
              <span className="whitespace-nowrap text-sm text-slate-600">{l.paid ? 'Pagado' : formatCOP(left)}</span>
            </div>
            {l.received > 0 && !l.paid && (
              <div className="my-2 h-2 rounded bg-slate-200">
                <div className="h-2 rounded bg-brand" style={{ width: `${Math.min(Math.floor((l.received * 100) / l.expected_amount), 100)}%` }} />
              </div>
            )}
            <p className="text-xs text-slate-500">
              {t.gave} {formatCOP(l.amount)}
              {l.expected_amount !== l.amount && ` · total ${formatCOP(l.expected_amount)}`}
              {l.received > 0 && ` · ${t.done.toLowerCase()} ${formatCOP(l.received)}`}
              {l.due_date && ` · ${formatDate(l.due_date)}`}
            </p>
            {l.note && <p className="line-clamp-2 text-xs text-slate-500 [overflow-wrap:anywhere]">{l.note}</p>}
            {late && <p className="text-xs text-red-700">Vencido</p>}
            {!l.paid &&
              (paying === l.id ? (
                <PaymentForm loan={l} onDone={() => setPaying(null)} />
              ) : (
                <div className="mt-2 flex gap-2">
                  <button className="rounded-lg border border-brand px-3 py-1 text-sm text-emerald-700" onClick={() => setPaying(l.id)}>
                    Abonar
                  </button>
                  <button
                    className="rounded-lg border border-brand px-3 py-1 text-sm text-emerald-700 disabled:opacity-60"
                    disabled={payAll.isPending}
                    onClick={() => payAll.mutate({ id: l.id, amount: left })}
                  >
                    {t.all}
                  </button>
                </div>
              ))}
          </section>
        )
      })}
    </div>
  )
}
