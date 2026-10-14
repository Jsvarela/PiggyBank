import { Link } from 'react-router-dom'
import BackupPanel from '../components/BackupPanel'
import InstallApp from '../components/InstallApp'
import ThemeToggle from '../components/ThemeToggle'

const links = [
  ['/recurrentes', 'Recurrentes', 'Arriendo, Netflix, salario y próximos pagos'],
  ['/cuentas', 'Cuentas', 'Efectivo, bancos, billeteras y tarjetas'],
  ['/categorias', 'Categorías', 'Organiza tus ingresos y gastos'],
  ['/importar', 'Importar extracto', 'Carga movimientos desde un CSV de tu banco'],
  ['/cuenta', 'Cuenta', 'Contraseña, sesiones, privacidad y eliminar cuenta'],
] as const

export default function More() {
  return (
    <div className="space-y-4">
      <ul className="divide-y rounded-xl bg-surface px-4 shadow-sm">
        {links.map(([to, title, hint]) => (
          <li key={to}>
            <Link to={to} className="block py-3">
              <span className="block font-medium">{title}</span>
              <span className="block text-xs text-slate-500">{hint}</span>
            </Link>
          </li>
        ))}
      </ul>
      <ThemeToggle />
      <InstallApp />
      <BackupPanel />
    </div>
  )
}
