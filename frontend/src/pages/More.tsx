import { Link } from 'react-router-dom'
import BackupPanel from '../components/BackupPanel'
import InstallApp from '../components/InstallApp'

const links = [
  ['/recurrentes', 'Recurrentes', 'Arriendo, Netflix, salario y próximos pagos'],
  ['/cuentas', 'Cuentas', 'Efectivo, bancos, billeteras y tarjetas'],
  ['/categorias', 'Categorías', 'Organiza tus ingresos y gastos'],
] as const

export default function More() {
  return (
    <div className="space-y-4">
      <ul className="divide-y rounded-xl bg-white px-4 shadow-sm">
        {links.map(([to, title, hint]) => (
          <li key={to}>
            <Link to={to} className="block py-3">
              <span className="block font-medium">{title}</span>
              <span className="block text-xs text-slate-500">{hint}</span>
            </Link>
          </li>
        ))}
      </ul>
      <InstallApp />
      <BackupPanel />
    </div>
  )
}
