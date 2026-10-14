import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useEffect } from 'react'
import { BrowserRouter, Route, Routes, useLocation } from 'react-router-dom'
import { ApiError } from './api/client'
import { useConfig, useMe } from './api/hooks'
import ErrorBoundary from './components/ErrorBoundary'
import Layout from './components/Layout'
import Loading from './components/Loading'
import { initAnalytics, trackPage } from './lib/analytics'
import { hadSession } from './lib/localCache'
import Account from './pages/Account'
import Accounts from './pages/Accounts'
import Budgets from './pages/Budgets'
import Categories from './pages/Categories'
import ForgotPassword from './pages/ForgotPassword'
import Goals from './pages/Goals'
import Home from './pages/Home'
import ImportCsv from './pages/ImportCsv'
import { Privacy, Terms } from './pages/Legal'
import Login from './pages/Login'
import More from './pages/More'
import NotFound from './pages/NotFound'
import Recurring from './pages/Recurring'
import ResetPassword from './pages/ResetPassword'
import Transactions from './pages/Transactions'
import VerifyEmail from './pages/VerifyEmail'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: (n, e) => !(e instanceof ApiError) && n < 2, refetchOnWindowFocus: false } },
})

/** Estadísticas opcionales: solo si el servidor las activó, y solo la ruta de cada pantalla. */
function Analytics() {
  const url = useConfig().data?.analytics_url ?? null
  const { pathname } = useLocation()
  useEffect(() => initAnalytics(url), [url])
  useEffect(() => trackPage(pathname), [pathname, url])
  return null
}

function Gate() {
  const { data: user, isLoading, error } = useMe()
  if (isLoading)
    return (
      <div className="p-4">
        <Loading />
      </div>
    )
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
        <Route path="/cuenta" element={<Account />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}

export default function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Analytics />
          <Routes>
            {/* públicas: se ven sin iniciar sesión (y desde un enlace de correo) */}
            <Route path="/olvide" element={<ForgotPassword />} />
            <Route path="/restablecer" element={<ResetPassword />} />
            <Route path="/verificar" element={<VerifyEmail />} />
            <Route path="/privacidad" element={<Privacy />} />
            <Route path="/terminos" element={<Terms />} />
            <Route path="*" element={<Gate />} />
          </Routes>
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}
