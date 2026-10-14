import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { api } from '../api/client'
import { useConfig } from '../api/hooks'
import PublicPage from '../components/PublicPage'

const schema = z.object({ email: z.email('Correo inválido') })

export default function ForgotPassword() {
  const config = useConfig().data
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')
  const { register, handleSubmit, formState } = useForm<{ email: string }>({ resolver: zodResolver(schema) })

  if (config && !config.email_enabled)
    return (
      <PublicPage title="Recuperar contraseña">
        <p className="text-sm text-slate-600">
          Esta instalación no tiene el envío de correos configurado, así que no se puede recuperar por correo. Quien administra la app puede
          restablecerla desde el servidor (ver DEPLOY.md, sección «Olvidé mi contraseña»).
        </p>
      </PublicPage>
    )

  return (
    <PublicPage title="Recuperar contraseña">
      {sent ? (
        <p className="rounded-xl bg-surface p-4 text-sm shadow-sm">
          Si ese correo tiene una cuenta, te enviamos un enlace para crear una contraseña nueva. Vale 30 minutos. Revisa también la carpeta de spam.
        </p>
      ) : (
        <form
          className="space-y-3"
          onSubmit={handleSubmit(async (v) => {
            setError('')
            try {
              await api('/auth/forgot-password', { method: 'POST', body: v })
              setSent(true)
            } catch (e) {
              setError((e as Error).message)
            }
          })}
        >
          <p className="text-sm text-slate-600">Escribe el correo de tu cuenta y te enviaremos un enlace.</p>
          <input type="email" autoComplete="email" placeholder="Correo" className="w-full rounded-lg border border-slate-300 p-3" {...register('email')} />
          {formState.errors.email && <p className="text-sm text-red-600">{formState.errors.email.message}</p>}
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button disabled={formState.isSubmitting} className="w-full rounded-lg bg-brand py-3 font-medium text-white disabled:opacity-60">
            {formState.isSubmitting ? 'Enviando…' : 'Enviar enlace'}
          </button>
        </form>
      )}
    </PublicPage>
  )
}
