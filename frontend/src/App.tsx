import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Route, Routes } from 'react-router-dom'

const queryClient = new QueryClient()

function Inicio() {
  return (
    <main className="mx-auto max-w-md p-4">
      <h1 className="text-2xl font-semibold">Finanzas</h1>
      <p className="text-slate-600">Próximamente: tus cuentas y movimientos.</p>
    </main>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Inicio />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
