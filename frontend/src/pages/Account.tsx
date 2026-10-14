import { zodResolver } from '@hookform/resolvers/zod'
import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router-dom'
import { z } from 'zod'
import { api } from '../api/client'
import { useConfig, useMe } from '../api/hooks'
import { queueDb } from '../lib/offlineQueue'
import { setSession } from '../lib/localCache'

const card = 'space-y-2 rounded-xl bg-surface p-4 shadow-sm'
const field = 'w-full rounded-lg border border-slate-300 p-2'

const passwordSchema = z
  .object({ current_password: z.string().min(1, 'Escribe tu contraseña actual'), new_password: z.string().min(8, 'Mínimo 8 caracteres'), confirm: z.string() })
  .refine((v) => v.new_password === v.confirm, { path: ['confirm'], message: 'Las contraseñas no coinciden' })
type PasswordValues = z.infer<typeof passwordSchema>

function ChangePassword() {
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)
  const { register, handleSubmit, reset, formState } = useForm<PasswordValues>({ resolver: zodResolver(passwordSchema) })
  const { errors } = formState
  return (
    <form
      className={card}
      onSubmit={handleSubmit(async ({ current_password, new_password }) => {
        setMsg(null)
        try {
          await api('/auth/change-password', { method: 'POST', body: { current_password, new_password } })
          reset()
          setMsg({ ok: true, text: 'Contraseña cambiada. Se cerraron las sesiones en tus otros dispositivos.' })
        } catch (e) {
          setMsg({ ok: false, text: (e as Error).message })
        }
      })}
    >
      <h2 className="font-medium">Cambiar contraseña</h2>
      <input type="password" autoComplete="current-password" placeholder="Contraseña actual" className={field} {...register('current_password')} />
      {errors.current_password && <p className="text-sm text-red-600">{errors.current_password.message}</p>}
      <input type="password" autoComplete="new-password" placeholder="Contraseña nueva" className={field} {...register('new_password')} />
      {errors.new_password && <p className="text-sm text-red-600">{errors.new_password.message}</p>}
      <input type="password" autoComplete="new-password" placeholder="Repite la nueva" className={field} {...register('confirm')} />
      {errors.confirm && <p className="text-sm text-red-600">{errors.confirm.message}</p>}
      {msg && <p className={`text-sm ${msg.ok ? 'text-emerald-700' : 'text-red-600'}`}>{msg.text}</p>}
      <button disabled={formState.isSubmitting} className="w-full rounded-lg bg-brand py-2 text-white disabled:opacity-60">
        Cambiar contraseña
      </button>
    </form>
  )
}

function DeleteAccount() {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function remove() {
    if (!confirm('Se borrarán TODOS tus datos (cuentas, movimientos, presupuestos, metas) y no se pueden recuperar. ¿Seguro?')) return
    setBusy(true)
    setError('')
    try {
      await api('/auth/account', { method: 'DELETE', body: { password } })
      await queueDb.pending.clear().catch(() => {}) // pendientes sin conexión de la cuenta borrada
      setSession(false)
      location.assign('/')
    } catch (e) {
      setError((e as Error).message)
      setBusy(false)
    }
  }

  return (
    <section className="space-y-2 rounded-xl border border-red-300 bg-surface p-4 shadow-sm">
      <h2 className="font-medium text-red-700">Eliminar cuenta</h2>
      <p className="text-sm text-slate-600">
        Borra tu usuario y todos tus datos de forma definitiva. Antes puedes descargar un respaldo en <Link to="/mas" className="underline">Más → Respaldo y exportación</Link>.
      </p>
      <input type="password" autoComplete="current-password" placeholder="Tu contraseña para confirmar" className={field} value={password} onChange={(e) => setPassword(e.target.value)} />
      {error && <p className="text-sm text-red-600">{error}</p>}
      <button disabled={!password || busy} className="w-full rounded-lg bg-red-700 py-2 text-white disabled:opacity-50" onClick={remove}>
        {busy ? 'Eliminando…' : 'Eliminar mi cuenta y todos mis datos'}
      </button>
    </section>
  )
}

export default function Account() {
  const qc = useQueryClient()
  const user = useMe().data
  const emailEnabled = useConfig().data?.email_enabled
  const [msg, setMsg] = useState('')

  return (
    <div className="space-y-4">
      <section className={card}>
        <h2 className="font-medium">Tu correo</h2>
        <p className="text-sm">
          {user?.email}{' '}
          {user?.email_verified ? (
            <span className="rounded bg-emerald-600/15 px-1.5 text-xs text-emerald-700">verificado</span>
          ) : (
            <span className="rounded bg-amber-50 px-1.5 text-xs text-amber-800">sin verificar</span>
          )}
        </p>
        {!user?.email_verified && emailEnabled && (
          <>
            <p className="text-xs text-slate-500">Verifícalo para poder recuperar tu contraseña por correo.</p>
            <button
              className="w-full rounded-lg border border-slate-300 py-2"
              onClick={async () => {
                try {
                  await api('/auth/send-verification', { method: 'POST' })
                  setMsg('Te enviamos el correo de verificación.')
                } catch (e) {
                  setMsg((e as Error).message)
                }
              }}
            >
              Reenviar correo de verificación
            </button>
            {msg && <p className="text-sm text-slate-600">{msg}</p>}
          </>
        )}
        {emailEnabled === false && <p className="text-xs text-slate-500">El envío de correos no está configurado en esta instalación.</p>}
      </section>

      <ChangePassword />

      <section className={card}>
        <h2 className="font-medium">Sesiones</h2>
        <p className="text-xs text-slate-500">Si perdiste un dispositivo, ciérrala en todos (también en este).</p>
        <button
          className="w-full rounded-lg border border-slate-300 py-2"
          onClick={async () => {
            await api('/auth/logout-all', { method: 'POST' })
            setSession(false)
            qc.clear()
            location.assign('/')
          }}
        >
          Cerrar sesión en todos los dispositivos
        </button>
      </section>

      <section className={card}>
        <h2 className="font-medium">Legal</h2>
        <Link to="/privacidad" className="block underline">
          Política de privacidad
        </Link>
        <Link to="/terminos" className="block underline">
          Términos de uso
        </Link>
      </section>

      <DeleteAccount />
    </div>
  )
}
