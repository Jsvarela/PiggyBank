import { useAccounts } from '../api/hooks'
import { discard, usePending } from '../lib/offlineQueue'
import { formatCOP } from '../lib/money'

/** Movimientos registrados sin conexión que todavía no llegaron al servidor. */
export default function PendingBanner() {
  const pending = usePending()
  const accounts = useAccounts().data ?? []
  if (pending.length === 0) return null
  const waiting = pending.filter((p) => !p.error).length

  return (
    <section className="space-y-1 rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800">
      {waiting > 0 && (
        <p>
          {waiting === 1 ? '1 movimiento guardado sin conexión. Se enviará solo' : `${waiting} movimientos guardados sin conexión. Se enviarán solos`}{' '}
          al volver internet; mientras tanto no cuentan en tus saldos.
        </p>
      )}
      {pending
        .filter((p) => p.error)
        .map((p) => (
          <p key={p.id} className="flex items-center justify-between gap-2 text-red-700">
            <span>
              No se pudo enviar {formatCOP(p.body.amount)} ({accounts.find((a) => a.id === p.body.account_id)?.name ?? 'cuenta'}):{' '}
              {p.error}
            </span>
            <button className="shrink-0 underline" onClick={() => discard(p.id)}>
              Descartar
            </button>
          </p>
        ))}
    </section>
  )
}
