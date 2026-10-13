import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { ApiError } from './api/client'
import { useMe } from './api/hooks'
import Layout from './components/Layout'
import Accounts from './pages/Accounts'
import Budgets from './pages/Budgets'
import Categories from './pages/Categories'
import Home from './pages/Home'
import Login from './pages/Login'
import Transactions from './pages/Transactions'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: (n, e) => !(e instanceof ApiError) && n < 2, refetchOnWindowFocus: false } },
})

function Gate() {
  const { data: user, isLoading } = useMe()
  if (isLoading) return <p className="p-4">Cargando…</p>
  if (!user) return <Login />
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/movimientos" element={<Transactions />} />
        <Route path="/presupuestos" element={<Budgets />} />
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
