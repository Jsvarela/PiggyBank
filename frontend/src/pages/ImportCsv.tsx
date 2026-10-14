import { useQueryClient } from '@tanstack/react-query'
import { formatDate, plural } from '../lib/format'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAccounts, useCategories } from '../api/hooks'
import type { CsvMapping, PreviewRow, StatementPreview } from '../api/types'
import { formatCOP } from '../lib/money'

const field = 'w-full rounded-lg border border-slate-300 bg-surface p-2'
const DEFAULT: CsvMapping = {
  date_col: 0, description_col: null, amount_col: null, debit_col: null, credit_col: null,
  date_format: 'dmy', decimal: ',', invert_sign: false, has_header: true,
}
type Choice = { on: boolean; category: number | null }

export default function ImportCsv() {
  const nav = useNavigate()
  const qc = useQueryClient()
  const accounts = (useAccounts().data ?? []).filter((a) => !a.archived)
  const categories = (useCategories().data ?? []).filter((c) => !c.archived)
  const [accountId, setAccountId] = useState<number>()
  const [text, setText] = useState('')
  const [info, setInfo] = useState<StatementPreview | null>(null)
  const [m, setM] = useState<CsvMapping>(DEFAULT)
  const [rows, setRows] = useState<PreviewRow[] | null>(null)
  const [choice, setChoice] = useState<Record<number, Choice>>({})
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const account = accountId ?? accounts[0]?.id

  async function run<T>(fn: () => Promise<T>) {
    setError('')
    setBusy(true)
    try {
      return await fn()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const call = (mapping?: CsvMapping) =>
    api<StatementPreview>('/import/csv/preview', { method: 'POST', body: { text, account_id: account, mapping } })

  const onFile = (f: File) =>
    run(async () => {
      const content = await f.text()
      const res = await api<StatementPreview>('/import/csv/preview', { method: 'POST', body: { text: content, account_id: account } })
      setText(content)
      setInfo(res)
      setM(res.suggested ?? DEFAULT)
      setRows(null)
    })

  const defaultCategory = (type: 'income' | 'expense' | null) => {
    const ofKind = categories.filter((c) => c.kind === type)
    return (ofKind.find((c) => c.name === (type === 'income' ? 'Otros ingresos' : 'Otros')) ?? ofKind[0])?.id ?? null
  }

  const showPreview = () =>
    run(async () => {
      const res = await call(m)
      setRows(res.rows)
      // los duplicados y las filas con error arrancan desmarcados
      setChoice(Object.fromEntries(res.rows.map((r) => [r.line, { on: !r.duplicate && !r.error, category: defaultCategory(r.type) }])))
    })

  const chosen = (rows ?? []).filter((r) => !r.error && choice[r.line]?.on)

  const confirm = () =>
    run(async () => {
      if (chosen.some((r) => choice[r.line].category === null)) throw new Error('Falta una categoría de ingreso o de gasto: créala primero en Categorías.')
      const items = chosen.map((r) => ({
        type: r.type, amount: r.amount, date: r.date, account_id: account, to_account_id: null,
        category_id: choice[r.line].category, description: r.description || null,
      }))
      await api('/transactions/bulk', { method: 'POST', body: { items } })
      await qc.invalidateQueries()
      nav('/movimientos')
    })

  const col = (label: string, value: number | null, set: (v: number | null) => void, optional = false) => (
    <label className="block text-sm text-slate-600">
      {label}
      <select className={field} value={value ?? ''} onChange={(e) => set(e.target.value === '' ? null : Number(e.target.value))}>
        {optional && <option value="">(ninguna)</option>}
        {info?.headers.map((h, i) => (
          <option key={i} value={i}>
            {i + 1}. {h}
          </option>
        ))}
      </select>
    </label>
  )
  const split = m.amount_col === null

  return (
    <div className="space-y-4">
      <section className="space-y-2 rounded-xl bg-surface p-4 shadow-sm">
        <h2 className="font-medium">1. Cuenta y archivo</h2>
        <select aria-label="Cuenta" className={field} value={account ?? ''} onChange={(e) => setAccountId(Number(e.target.value))}>
          {accounts.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </select>
        <input type="file" accept=".csv,text/csv,text/plain" disabled={!account || busy} onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])} />
        <p className="text-xs text-slate-500">Descarga el extracto como CSV desde la web de tu banco. La primera fila debe ser de encabezados.</p>
      </section>

      {info && (
        <section className="space-y-2 rounded-xl bg-surface p-4 shadow-sm">
          <h2 className="font-medium">2. ¿Qué es cada columna?</h2>
          <div className="overflow-x-auto text-xs">
            <table className="w-full whitespace-nowrap">
              <thead>
                <tr className="text-left text-slate-500">
                  {info.headers.map((h, i) => (
                    <th key={i} className="pr-3">
                      {i + 1}. {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {info.sample.map((r, i) => (
                  <tr key={i}>
                    {r.map((c, j) => (
                      <td key={j} className="pr-3">
                        {c}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {col('Fecha', m.date_col, (v) => setM({ ...m, date_col: v ?? 0 }))}
          {col('Descripción', m.description_col, (v) => setM({ ...m, description_col: v }), true)}
          <label className="block text-sm text-slate-600">
            Monto en
            <select className={field} value={split ? 'split' : 'single'} onChange={(e) => setM(e.target.value === 'split' ? { ...m, amount_col: null, debit_col: 0, credit_col: 0 } : { ...m, amount_col: 0, debit_col: null, credit_col: null })}>
              <option value="single">una columna (negativo = gasto)</option>
              <option value="split">dos columnas (débito y crédito)</option>
            </select>
          </label>
          {split ? (
            <>
              {col('Débito (gastos)', m.debit_col, (v) => setM({ ...m, debit_col: v }), true)}
              {col('Crédito (ingresos)', m.credit_col, (v) => setM({ ...m, credit_col: v }), true)}
            </>
          ) : (
            <>
              {col('Monto', m.amount_col, (v) => setM({ ...m, amount_col: v ?? 0 }))}
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={m.invert_sign} onChange={(e) => setM({ ...m, invert_sign: e.target.checked })} /> Las compras vienen en positivo (tarjeta de crédito)
              </label>
            </>
          )}
          <div className="grid grid-cols-2 gap-2">
            <label className="text-sm text-slate-600">
              Fecha como
              <select className={field} value={m.date_format} onChange={(e) => setM({ ...m, date_format: e.target.value as CsvMapping['date_format'] })}>
                <option value="dmy">día/mes/año</option>
                <option value="mdy">mes/día/año</option>
                <option value="ymd">año-mes-día</option>
              </select>
            </label>
            <label className="text-sm text-slate-600">
              Decimales con
              <select className={field} value={m.decimal} onChange={(e) => setM({ ...m, decimal: e.target.value as ',' | '.' })}>
                <option value=",">coma (1.234,50)</option>
                <option value=".">punto (1,234.50)</option>
              </select>
            </label>
          </div>
          <button disabled={busy} className="w-full rounded-lg bg-brand py-2 text-white disabled:opacity-60" onClick={showPreview}>
            Ver vista previa
          </button>
        </section>
      )}

      {rows && (
        <section className="space-y-2 rounded-xl bg-surface p-4 shadow-sm">
          <h2 className="font-medium">3. Revisa y confirma</h2>
          <p className="text-xs text-slate-500">Los duplicados (ya existe un movimiento igual) y las filas con error vienen desmarcados.</p>
          <ul className="divide-y">
            {rows.map((r) => (
              <li key={r.line} className={`py-2 text-sm ${r.error ? 'text-slate-500' : ''}`}>
                {r.error ? (
                  <p>
                    Fila {r.line}: <span className="text-red-600">{r.error}</span>
                  </p>
                ) : (
                  <div className="flex items-start gap-2">
                    <input type="checkbox" aria-label={`Importar fila ${r.line}`} className="mt-1" checked={choice[r.line]?.on ?? false} onChange={(e) => setChoice({ ...choice, [r.line]: { ...choice[r.line], on: e.target.checked } })} />
                    <div className="min-w-0 flex-1">
                      <p className="flex justify-between gap-2">
                        <span className="truncate">{r.description || '(sin descripción)'}</span>
                        <span className={`whitespace-nowrap ${r.type === 'income' ? 'text-emerald-700' : 'text-red-700'}`}>
                          {r.type === 'income' ? '+' : '-'}
                          {formatCOP(r.amount ?? 0)}
                        </span>
                      </p>
                      <p className="text-xs text-slate-500">
                        {r.date && formatDate(r.date)}
                        {r.duplicate && <span className="ml-2 rounded bg-amber-50 px-1 text-amber-700">posible duplicado</span>}
                      </p>
                      <select aria-label={`Categoría fila ${r.line}`} className="mt-1 w-full rounded border border-slate-300 bg-surface p-1 text-base" value={choice[r.line]?.category ?? ''} onChange={(e) => setChoice({ ...choice, [r.line]: { ...choice[r.line], category: Number(e.target.value) } })}>
                        {categories.filter((c) => c.kind === r.type).map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                )}
              </li>
            ))}
          </ul>
          <button disabled={busy || chosen.length === 0} className="w-full rounded-lg bg-brand py-2 text-white disabled:opacity-60" onClick={confirm}>
            Importar {plural(chosen.length, 'movimiento', 'movimientos')}
          </button>
        </section>
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  )
}
