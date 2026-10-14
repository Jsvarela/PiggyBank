import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router-dom'
import { z } from 'zod'
import { useApiMutation } from '../api/hooks'
import { ACCOUNT_TYPES, type AccountBody, type AccountType } from '../api/types'
import { useEditor } from './editor'

const KEY = 'onboardingHidden'
const schema = z.object({
  name: z.string().trim().min(1, 'Ponle un nombre'),
  type: z.enum(['cash', 'bank', 'digital_wallet', 'credit_card', 'savings']),
  initial_balance: z.number({ error: 'Ingresa un número (puede ser 0)' }).int('Sin decimales'),
  archived: z.boolean(),
})

const hidden = () => {
  try {
    return localStorage.getItem(KEY) === '1'
  } catch {
    return false
  }
}

function FirstAccount() {
  const create = useApiMutation<AccountBody>('POST', () => '/accounts')
  const { register, handleSubmit, formState } = useForm<AccountBody>({
    resolver: zodResolver(schema),
    defaultValues: { name: '', type: 'cash', initial_balance: 0, archived: false },
  })
  const { errors } = formState
  const field = 'w-full rounded-lg border border-slate-300 p-2'
  return (
    <form className="space-y-2" onSubmit={handleSubmit((v) => create.mutate(v))}>
      <input placeholder="Nombre (Efectivo, Bancolombia, Nequi…)" className={field} {...register('name')} />
      {errors.name && <p className="text-sm text-red-600">{errors.name.message}</p>}
      <select aria-label="Tipo de cuenta" className={field} {...register('type')}>
        {(Object.keys(ACCOUNT_TYPES) as AccountType[]).map((t) => (
          <option key={t} value={t}>
            {ACCOUNT_TYPES[t]}
          </option>
        ))}
      </select>
      <label className="block text-xs text-slate-600">
        ¿Cuánto tienes hoy en esta cuenta? (en una tarjeta de crédito, lo que debes, en negativo)
        <input type="number" inputMode="numeric" className={`mt-1 ${field}`} {...register('initial_balance', { valueAsNumber: true })} />
      </label>
      {errors.initial_balance && <p className="text-sm text-red-600">{errors.initial_balance.message}</p>}
      {create.error && <p className="text-sm text-red-600">{create.error.message}</p>}
      <button disabled={create.isPending} className="w-full rounded-lg bg-brand py-2 text-white disabled:opacity-60">
        Crear cuenta
      </button>
    </form>
  )
}

/** Guía de primeros pasos. Se arma sola con los datos que ya hay: no guarda estado propio. */
export default function Onboarding({ hasAccount, hasTransaction }: { hasAccount: boolean; hasTransaction: boolean }) {
  const [gone, setGone] = useState(hidden)
  const openEditor = useEditor()
  if (gone || (hasAccount && hasTransaction)) return null

  const step = (done: boolean) => (
    <span aria-hidden className={`mr-2 inline-block h-5 w-5 rounded-full border text-center text-xs leading-5 ${done ? 'border-brand bg-brand text-white' : 'border-slate-300'}`}>
      {done ? '✓' : ''}
    </span>
  )

  return (
    <section className="space-y-3 rounded-xl border border-brand bg-surface p-4 shadow-sm">
      <h2 className="font-semibold">¡Bienvenido! Empecemos en 2 pasos</h2>

      <div>
        <p className="mb-1 font-medium">
          {step(hasAccount)}1. Crea tu primera cuenta
        </p>
        {!hasAccount && <FirstAccount />}
      </div>

      <div>
        <p className="mb-1 font-medium">
          {step(hasTransaction)}2. Registra tu primer movimiento
        </p>
        {hasAccount && !hasTransaction && (
          <>
            <p className="mb-2 text-xs text-slate-600">Toca el botón verde «+» (o este) en cualquier pantalla: monto, categoría y listo.</p>
            <button className="w-full rounded-lg bg-brand py-2 text-white" onClick={() => openEditor()}>
              Registrar un gasto
            </button>
          </>
        )}
      </div>

      <p className="text-xs text-slate-600">
        Después puedes fijar un <Link to="/presupuestos" className="underline">presupuesto</Link> e <Link to="/mas" className="underline">instalar la app</Link> en tu celular.
      </p>
      <button
        className="text-xs text-slate-500 underline"
        onClick={() => {
          try {
            localStorage.setItem(KEY, '1')
          } catch {
            /* ver arriba */
          }
          setGone(true)
        }}
      >
        Ocultar esta guía
      </button>
    </section>
  )
}
