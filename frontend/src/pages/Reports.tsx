import { useState } from 'react'
import { useMonthlyReport, useTrend } from '../api/hooks'
import Loading from '../components/Loading'
import { todayBogota } from '../lib/dates'
import { formatMonth, shiftMonth } from '../lib/format'
import { formatCOP } from '../lib/money'

// Ingresos y gastos se distinguen por tono (azul / naranja, seguros para daltonismo), por la leyenda y por los
// montos escritos: el color nunca es la única pista.
const INCOME = 'bg-sky-500'
const EXPENSE = 'bg-orange-500'
const TOP = 6 // el resto de categorías se junta en «Otras»

// menos del 1 % no es «0 %»: ese gasto sí existe
const pct = (n: number, total: number) => (n * 100 < total ? '<1%' : `${Math.round((n * 100) / total)}%`)

const shortMonth = (ym: string) => formatMonth(ym).split(' ')[0].slice(0, 3)

function CategoryBars({ month }: { month: string }) {
  const report = useMonthlyReport(month).data
  if (!report) return <Loading />
  const rows = report.categories.filter((c) => c.amount > 0)
  if (rows.length === 0) return <p className="text-sm text-slate-500">Sin gastos en {formatMonth(month)}.</p>
  const shown = rows.slice(0, TOP)
  const rest = rows.slice(TOP).reduce((s, c) => s + c.amount, 0)
  const bars = rest > 0 ? [...shown, { category_id: -1, name: 'Otras', amount: rest }] : shown
  const total = rows.reduce((s, c) => s + c.amount, 0)
  const max = Math.max(...bars.map((b) => b.amount))

  return (
    <ul className="space-y-3">
      {bars.map((b) => (
        <li key={b.category_id}>
          <div className="flex flex-wrap items-baseline justify-between gap-x-3 text-sm">
            <span className="min-w-0 grow basis-32 [overflow-wrap:anywhere]">{b.name}</span>
            <span className="whitespace-nowrap text-slate-600">
              {formatCOP(b.amount)} · {pct(b.amount, total)}
            </span>
          </div>
          <div className="mt-1 h-3 rounded bg-slate-200" aria-hidden>
            <div className={`h-3 rounded ${EXPENSE}`} style={{ width: `${Math.max((b.amount * 100) / max, 1)}%` }} />
          </div>
        </li>
      ))}
    </ul>
  )
}

function Trend({ month }: { month: string }) {
  const points = useTrend(month, 6).data
  if (!points) return <Loading />
  const max = Math.max(...points.flatMap((p) => [p.income, p.expense]), 1)
  // un monto chico junto a uno enorme sigue visible: mínimo 2 px (y nada si es cero)
  const h = (n: number) => (n > 0 ? `max(${(n * 100) / max}%, 2px)` : '0')

  return (
    <div className="space-y-3">
      <div className="flex gap-4 text-sm" aria-hidden>
        <span className="flex items-center gap-1.5">
          <span className={`h-3 w-3 rounded-sm ${INCOME}`} /> Ingresos
        </span>
        <span className="flex items-center gap-1.5">
          <span className={`h-3 w-3 rounded-sm ${EXPENSE}`} /> Gastos
        </span>
      </div>
      <div className="flex h-40 items-end gap-2" role="img" aria-label="Ingresos y gastos de los últimos 6 meses">
        {points.map((p) => (
          <div key={p.month} className="flex h-full min-w-0 flex-1 flex-col justify-end">
            <div className="flex h-full items-end justify-center gap-0.5 border-b border-slate-300">
              <div className={`w-1/2 max-w-5 rounded-t ${INCOME}`} style={{ height: h(p.income) }} title={`Ingresos ${formatCOP(p.income)}`} />
              <div className={`w-1/2 max-w-5 rounded-t ${EXPENSE}`} style={{ height: h(p.expense) }} title={`Gastos ${formatCOP(p.expense)}`} />
            </div>
            <p className="mt-1 text-center text-xs text-slate-600">{shortMonth(p.month)}</p>
          </div>
        ))}
      </div>
      <details>
        <summary className="cursor-pointer text-sm text-slate-600 underline">Ver los montos en una tabla</summary>
        <table className="mt-2 w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500">
              <th className="py-1 font-normal">Mes</th>
              <th className="py-1 text-right font-normal">Ingresos</th>
              <th className="py-1 text-right font-normal">Gastos</th>
            </tr>
          </thead>
          <tbody>
            {points.map((p) => (
              <tr key={p.month} className="border-t">
                <td className="py-1">{formatMonth(p.month)}</td>
                <td className="whitespace-nowrap py-1 text-right">{formatCOP(p.income)}</td>
                <td className="whitespace-nowrap py-1 text-right">{formatCOP(p.expense)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  )
}

export default function Reports() {
  const [month, setMonth] = useState(todayBogota().slice(0, 7))
  const report = useMonthlyReport(month).data

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

      {report && (
        <section className="grid grid-cols-1 gap-3 min-[400px]:grid-cols-3">
          {(
            [
              ['Ingresos', report.income],
              ['Gastos', report.expense],
              ['Ahorro del mes', report.income - report.expense],
            ] as const
          ).map(([label, value]) => (
            <div key={label} className="rounded-xl bg-surface p-3 shadow-sm">
              <p className="text-xs text-slate-500">{label}</p>
              <p className="font-semibold [overflow-wrap:anywhere]">{formatCOP(value)}</p>
            </div>
          ))}
        </section>
      )}

      <section className="rounded-xl bg-surface p-4 shadow-sm">
        <h2 className="mb-3 font-medium">En qué gastaste</h2>
        <CategoryBars month={month} />
      </section>

      <section className="rounded-xl bg-surface p-4 shadow-sm">
        <h2 className="mb-3 font-medium">Últimos 6 meses</h2>
        <Trend month={month} />
      </section>
    </div>
  )
}
