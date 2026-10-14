import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

/** Marco de las páginas que se ven sin iniciar sesión (recuperar clave, políticas…). */
export default function PublicPage({ title, children }: { title: string; children: ReactNode }) {
  return (
    <main className="mx-auto max-w-xl space-y-4 p-4 pt-10">
      <Link to="/" className="text-sm text-slate-600">
        ‹ Volver
      </Link>
      <h1 className="text-2xl font-semibold">{title}</h1>
      {children}
    </main>
  )
}
