import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useSearchParams } from 'react-router-dom'
import { z } from 'zod'
import { api } from '../api/client'
import PublicPage from '../components/PublicPage'

const schema = z
  .object({ password: z.string().min(8, 'Mínimo 8 caracteres'), confirm: z.string() })
  .refine((v) => v.password === v.confirm, { path: ['confirm'], message: 'Las contraseñas no coinciden' })
type Values = z.infer<typeof schema>

export default function ResetPassword() {
  const token = useSearchParams()[0].get('token')
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')
  const { register, handleSubmit, formState } = useForm<Values>({ resolver: zodResolver(schema) })
  const { errors } = formState

  if (!token)
    return (
      <PublicPage title="Contraseña nueva">
        <p className="text-sm text-red-600">Falta el enlace. Pide uno nuevo desde «¿Olvidaste tu contraseña?».</p>
      </PublicPage>
    )
  if (done)
    return (
      <PublicPage title="Contraseña nueva">
        <p className="text-sm">Listo, tu contraseña cambió y se cerraron las sesiones abiertas.</p>
        <Link to="/" className="inline-block rounded-lg bg-brand px-4 py-2 text-white">
          Iniciar sesión
        </Link>
      </PublicPage>
    )

  return (
    <PublicPage title="Contraseña nueva">
      <form
        className="space-y-3"
        onSubmit={handleSubmit(async (v) => {
          setError('')
          try {
            await api('/auth/reset-password', { method: 'POST', body: { token, password: v.password } })
            setDone(true)
          } catch (e) {
            setError((e as Error).message)
          }
        })}
      >
        <input type="password" autoComplete="new-password" placeholder="Contraseña nueva" className="w-full rounded-lg border border-slate-300 p-3" {...register('password')} />
        {errors.password && <p className="text-sm text-red-600">{errors.password.message}</p>}
        <input type="password" autoComplete="new-password" placeholder="Repítela" className="w-full rounded-lg border border-slate-300 p-3" {...register('confirm')} />
        {errors.confirm && <p className="text-sm text-red-600">{errors.confirm.message}</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button disabled={formState.isSubmitting} className="w-full rounded-lg bg-brand py-3 font-medium text-white disabled:opacity-60">
          Guardar contraseña
        </button>
      </form>
    </PublicPage>
  )
}
