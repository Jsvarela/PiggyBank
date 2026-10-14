import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="space-y-3 py-10 text-center">
      <p className="text-5xl font-semibold text-slate-500">404</p>
      <h1 className="text-xl font-semibold">Esta página no existe</h1>
      <p className="text-sm text-slate-600">Puede que el enlace esté mal escrito o que ya no exista.</p>
      <Link to="/" className="inline-block rounded-lg bg-brand px-4 py-2 text-white">
        Ir al inicio
      </Link>
    </div>
  )
}
