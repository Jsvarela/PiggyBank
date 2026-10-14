import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import Loading from '../components/Loading'
import PublicPage from '../components/PublicPage'

export default function VerifyEmail() {
  const token = useSearchParams()[0].get('token')
  const qc = useQueryClient()
  const [state, setState] = useState<'loading' | 'ok' | string>(token ? 'loading' : 'Falta el enlace de verificación.')

  useEffect(() => {
    if (!token) return
    api('/auth/verify-email', { method: 'POST', body: { token } })
      .then(() => {
        setState('ok')
        qc.invalidateQueries({ queryKey: ['me'] })
      })
      .catch((e: Error) => setState(e.message))
  }, [token, qc])

  return (
    <PublicPage title="Verificar correo">
      {state === 'loading' && <Loading />}
      {state === 'ok' && <p className="text-sm">¡Correo confirmado! Ya puedes recuperar tu contraseña por correo si la olvidas.</p>}
      {state !== 'loading' && state !== 'ok' && <p className="text-sm text-red-600">{state}</p>}
      {state !== 'loading' && (
        <Link to="/" className="inline-block rounded-lg bg-brand px-4 py-2 text-white">
          Ir a la app
        </Link>
      )}
    </PublicPage>
  )
}
