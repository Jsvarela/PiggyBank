import { useQueryClient } from '@tanstack/react-query'
import { useRef, useState } from 'react'
import { api } from '../api/client'

const link = 'block rounded-lg border border-slate-300 py-2 text-center'

export default function BackupPanel() {
  const qc = useQueryClient()
  const file = useRef<HTMLInputElement>(null)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)

  async function restore(f: File) {
    if (!confirm('Esto REEMPLAZA todos tus datos actuales por los del respaldo. ¿Continuar?')) return
    try {
      const r = await api<{ transactions: number }>('/import/backup', { method: 'POST', body: JSON.parse(await f.text()) })
      await qc.invalidateQueries()
      setMsg({ ok: true, text: `Restaurado: ${r.transactions} movimientos.` })
    } catch (e) {
      setMsg({ ok: false, text: e instanceof SyntaxError ? 'El archivo no es un respaldo válido.' : (e as Error).message })
    } finally {
      if (file.current) file.current.value = ''
    }
  }

  return (
    <section className="space-y-2 rounded-xl bg-white p-4 shadow-sm">
      <h2 className="font-medium">Respaldo y exportación</h2>
      <a className={link} href="/api/export/backup.json" download>
        Descargar respaldo completo (JSON)
      </a>
      <a className={link} href="/api/export/transactions.csv" download>
        Exportar movimientos (CSV)
      </a>
      <button className={`w-full ${link}`} onClick={() => file.current?.click()}>
        Restaurar desde un respaldo…
      </button>
      <input ref={file} type="file" accept="application/json,.json" hidden onChange={(e) => e.target.files?.[0] && restore(e.target.files[0])} />
      {msg && <p className={`text-sm ${msg.ok ? 'text-emerald-700' : 'text-red-600'}`}>{msg.text}</p>}
      <p className="text-xs text-slate-500">Descarga un respaldo de vez en cuando: el plan gratuito de la base de datos solo guarda 6 horas de historial.</p>
    </section>
  )
}
