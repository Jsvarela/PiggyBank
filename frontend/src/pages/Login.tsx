import { zodResolver } from '@hookform/resolvers/zod'
import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { api } from '../api/client'

const schema = z.object({
  email: z.email('Correo inválido'),
  password: z.string().min(8, 'Mínimo 8 caracteres'),
})
type Values = z.infer<typeof schema>

export default function Login() {
  const qc = useQueryClient()
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')
  const { register, handleSubmit, formState } = useForm<Values>({ resolver: zodResolver(schema) })

  const onSubmit = handleSubmit(async (v) => {
    setError('')
    try {
      if (creating) await api('/auth/register', { method: 'POST', body: v })
      await api('/auth/login', { method: 'POST', body: v })
      await qc.invalidateQueries({ queryKey: ['me'] })
    } catch (e) {
      setError((e as Error).message)
    }
  })

  const { errors } = formState
  return (
    <form onSubmit={onSubmit} className="mx-auto mt-16 max-w-sm space-y-3 p-4">
      <h1 className="text-2xl font-semibold">{creating ? 'Crear tu usuario' : 'Iniciar sesión'}</h1>
      <input type="email" placeholder="Correo" autoComplete="email" className="w-full rounded-lg border border-slate-300 p-3" {...register('email')} />
      {errors.email && <p className="text-sm text-red-600">{errors.email.message}</p>}
      <input
        type="password"
        placeholder="Contraseña"
        autoComplete={creating ? 'new-password' : 'current-password'}
        className="w-full rounded-lg border border-slate-300 p-3"
        {...register('password')}
      />
      {errors.password && <p className="text-sm text-red-600">{errors.password.message}</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}
      <button className="w-full rounded-lg bg-emerald-600 py-3 font-medium text-white">{creating ? 'Crear y entrar' : 'Entrar'}</button>
      <button type="button" className="w-full text-sm text-slate-600" onClick={() => setCreating(!creating)}>
        {creating ? 'Ya tengo usuario' : 'Primera vez: crear usuario'}
      </button>
    </form>
  )
}
