import { Link } from 'react-router-dom'
import { useBudgetStatus } from '../api/hooks'
import { formatPercent } from '../lib/format'

/** Banner del Inicio: solo aparece si alguna categoría pasó su umbral o su límite. */
export default function BudgetAlerts() {
  const alerts = (useBudgetStatus().data ?? []).filter((b) => b.alert !== 'ok')
  if (alerts.length === 0) return null
  return (
    <Link to="/presupuestos" className="block space-y-1 rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm">
      {alerts.map((b) => (
        <p key={b.budget_id} className={`[overflow-wrap:anywhere] ${b.alert === 'exceeded' ? 'font-medium text-red-700' : 'text-amber-800'}`}>
          {b.alert === 'exceeded' ? `Superaste el presupuesto de ${b.category_name}` : `${b.category_name}: vas en ${formatPercent(b.percent)} del presupuesto`}
        </p>
      ))}
    </Link>
  )
}
