import { Link } from 'react-router-dom'
import { useMe } from '../api/hooks'
import BackupPanel from '../components/BackupPanel'
import InstallApp from '../components/InstallApp'
import ThemeToggle from '../components/ThemeToggle'

const links = [
  ['/ayuda', 'Ayuda rápida', 'Guía sencilla de qué hace cada parte de la app'],
  ['/recurrentes', 'Recurrentes', 'Arriendo, Netflix, salario y próximos pagos'],
  ['/informes', 'Informes', 'Gráficos de en qué gastas y cómo vas mes a mes'],
  ['/prestamos', 'Préstamos y deudas', 'Lo que te deben, lo que debes y cuándo se paga'],
  ['/cuentas', 'Cuentas', 'Efectivo, bancos, billeteras y tarjetas'],
  ['/categorias', 'Categorías', 'Organiza tus ingresos y gastos'],
  ['/importar', 'Importar extracto', 'Carga movimientos desde un CSV de tu banco'],
  ['/cuenta', 'Cuenta', 'Contraseña, sesiones, privacidad y eliminar cuenta'],
] as const

export default function More() {
  const admin = useMe().data?.is_admin
  return (
    <div className="space-y-4">
      <ul className="divide-y rounded-xl bg-surface px-4 shadow-sm">
        {[...links, ...(admin ? ([['/invitar', 'Invitar', 'Da acceso a otra persona con un código']] as const) : [])].map(([to, title, hint]) => (
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
