import { useDashboard } from '../api/hooks'
import { formatMonth } from '../lib/format'
import BudgetAlerts from '../components/BudgetAlerts'
import Onboarding from '../components/Onboarding'
import TransactionRow from '../components/TransactionRow'
import UpcomingList from '../components/UpcomingList'
import { formatCOP } from '../lib/money'

export default function Home() {
  const { data, isLoading, error } = useDashboard()
  if (isLoading) return <p>Cargando…</p>
  if (error || !data) return <p className="text-red-600">No se pudo cargar el inicio.</p>

  const accounts = data.accounts.filter((a) => !a.archived || a.balance !== 0)
  return (
    <div className="space-y-4">
      <Onboarding hasAccount={data.accounts.some((a) => !a.archived)} hasTransaction={data.recent.length > 0} />
      <BudgetAlerts />
      <section className="rounded-xl bg-surface p-4 shadow-sm">
        <p className="text-sm text-slate-500">Patrimonio total</p>
        {/* los montos nunca se recortan: si son enormes, la letra baja de tamaño y, como último recurso, se parte entre dígitos */}
        <p className="text-2xl font-semibold [overflow-wrap:anywhere] sm:text-3xl">{formatCOP(data.net_worth)}</p>
      </section>

      {/* lado a lado si los montos son cortos; apiladas en pantallas angostas si no caben en media columna */}
      <section className={`grid gap-3 ${[data.income, data.expense].every((n) => formatCOP(n).length <= 11) ? 'grid-cols-2' : 'grid-cols-1 min-[400px]:grid-cols-2'}`}>
        <div className="rounded-xl bg-surface p-3 shadow-sm">
          <p className="text-sm text-slate-500">Ingresos de {formatMonth(data.month)}</p>
          <p className="text-lg text-emerald-700 [overflow-wrap:anywhere]">{formatCOP(data.income)}</p>
        </div>
        <div className="rounded-xl bg-surface p-3 shadow-sm">
          <p className="text-sm text-slate-500">Gastos de {formatMonth(data.month)}</p>
          <p className="text-lg text-red-700 [overflow-wrap:anywhere]">{formatCOP(data.expense)}</p>
        </div>
      </section>

      <section className="rounded-xl bg-surface p-4 shadow-sm">
        <h2 className="mb-2 font-medium">Cuentas</h2>
        {accounts.length === 0 && <p className="text-sm text-slate-500">Crea tu primera cuenta en la pestaña Cuentas.</p>}
        <ul className="divide-y">
          {accounts.map((a) => (
            <li key={a.id} className="flex items-start justify-between gap-3 py-2">
              <span className="min-w-0 [overflow-wrap:anywhere]">{a.name}</span>
              <span className={`shrink-0 whitespace-nowrap ${a.balance < 0 ? 'text-red-700' : ''}`}>{formatCOP(a.balance)}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-xl bg-surface p-4 shadow-sm">
        <h2 className="mb-2 font-medium">Próximos pagos</h2>
        <UpcomingList limit={5} />
      </section>

      <section className="rounded-xl bg-surface p-4 shadow-sm">
        <h2 className="mb-2 font-medium">Últimos movimientos</h2>
        {data.recent.length === 0 && <p className="text-sm text-slate-500">Aún no hay movimientos. Usa el botón +.</p>}
        <ul className="divide-y">
          {data.recent.map((t) => (
            <TransactionRow key={t.id} tx={t} />
          ))}
        </ul>
      </section>
    </div>
  )
}
