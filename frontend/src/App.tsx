import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { ApiError } from './api/client'
import { useMe } from './api/hooks'
import Layout from './components/Layout'
import { hadSession } from './lib/localCache'
import Accounts from './pages/Accounts'
import Budgets from './pages/Budgets'
import Categories from './pages/Categories'
import Goals from './pages/Goals'
import Home from './pages/Home'
import ImportCsv from './pages/ImportCsv'
import Login from './pages/Login'
import More from './pages/More'
import Recurring from './pages/Recurring'
import Transactions from './pages/Transactions'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: (n, e) => !(e instanceof ApiError) && n < 2, refetchOnWindowFocus: false } },
})

function Gate() {
  const { data: user, isLoading, error } = useMe()
  if (isLoading) return <p className="p-4">Cargando…</p>
  // sin internet (no es un 401) y ya había sesión: se abre la app en vez de pedir login
  const offline = !user && error !== null && !(error instanceof ApiError) && hadSession()
  if (!user && !offline) return <Login />
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/movimientos" element={<Transactions />} />
        <Route path="/presupuestos" element={<Budgets />} />
        <Route path="/metas" element={<Goals />} />
        <Route path="/mas" element={<More />} />
        <Route path="/recurrentes" element={<Recurring />} />
        <Route path="/importar" element={<ImportCsv />} />
        <Route path="/cuentas" element={<Accounts />} />
        <Route path="/categorias" element={<Categories />} />
      </Route>
    </Routes>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Gate />
      </BrowserRouter>
    </QueryClientProvider>
  )
}
