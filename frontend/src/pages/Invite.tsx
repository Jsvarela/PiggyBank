import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../api/client'
import { useInvites, useMe } from '../api/hooks'
import { formatDate } from '../lib/format'

export default function Invite() {
  const me = useMe().data
  const invites = useInvites()
  const qc = useQueryClient()
  const [link, setLink] = useState('')
  const [copied, setCopied] = useState(false)

  const create = useMutation({
    mutationFn: () => api<{ code: string }>('/auth/invites', { method: 'POST' }),
    onSuccess: (r) => {
      setCopied(false)
      setLink(`${location.origin}/?invitacion=${encodeURIComponent(r.code)}`)
      qc.invalidateQueries({ queryKey: ['invites'] })
    },
  })
  const revoke = useMutation({
    mutationFn: (id: number) => api(`/auth/invites/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['invites'] }),
  })

  if (me && !me.is_admin) return <p className="text-sm text-slate-600">Solo quien administra la app puede invitar.</p>

  return (
    <div className="space-y-4">
      <section className="space-y-2 rounded-xl bg-surface p-4 shadow-sm">
        <p className="text-sm text-slate-600">Cada enlace sirve para una sola persona y vence en 7 días.</p>
        <button disabled={create.isPending} className="w-full rounded-lg bg-brand py-3 font-medium text-white disabled:opacity-60" onClick={() => create.mutate()}>
          {create.isPending ? 'Creando…' : 'Crear invitación'}
        </button>
        {create.error && <p className="text-sm text-red-600">{create.error.message}</p>}
        {link && (
          <div className="space-y-2">
            <p className="text-xs text-slate-600">Cópialo ahora: por seguridad no se vuelve a mostrar.</p>
            <input readOnly value={link} className="w-full rounded-lg border border-slate-300 p-2 text-xs" onFocus={(e) => e.currentTarget.select()} />
            <button
              className="text-sm underline"
              onClick={() => navigator.clipboard.writeText(link).then(() => setCopied(true), () => {})}
            >
              {copied ? 'Copiado' : 'Copiar enlace'}
            </button>
          </div>
        )}
      </section>

      <ul className="divide-y rounded-xl bg-surface px-4 shadow-sm">
        {(invites.data ?? []).length === 0 && <li className="py-3 text-sm text-slate-500">Aún no has invitado a nadie.</li>}
        {(invites.data ?? []).map((i) => (
          <li key={i.id} className="flex items-center justify-between gap-2 py-3 text-sm">
            <span className="min-w-0">
              <span className="block font-medium capitalize">{i.status}</span>
              <span className="block truncate text-xs text-slate-500">
                {i.used_by_email ?? `Vence ${formatDate(i.expires_at.slice(0, 10))}`}
              </span>
            </span>
            {i.status === 'pendiente' && (
              <button className="shrink-0 text-red-700 underline" onClick={() => revoke.mutate(i.id)}>
                Revocar
              </button>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}
