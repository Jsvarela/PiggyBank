import Dexie, { type Table } from 'dexie'
import { useSyncExternalStore } from 'react'
import { ApiError, api } from '../api/client'
import type { TransactionBody } from '../api/types'

/** Movimiento creado sin conexión, a la espera de enviarse. `id` lo genera el cliente. */
export interface Pending {
  id: string
  body: TransactionBody
  createdAt: number
  error?: string // el servidor lo rechazó: no se reintenta solo
}

class QueueDb extends Dexie {
  pending!: Table<Pending, string>
  constructor() {
    super('finanzas-offline')
    this.version(1).stores({ pending: 'id, createdAt' })
  }
}
export const queueDb = new QueueDb()

// Copia en memoria para que React pueda leerla de forma síncrona (useSyncExternalStore).
let snapshot: Pending[] = []
const listeners = new Set<() => void>()

export const getPending = () => queueDb.pending.orderBy('createdAt').toArray()

async function refresh() {
  snapshot = await getPending()
  listeners.forEach((l) => l())
}
refresh().catch(() => {}) // IndexedDB no disponible (modo privado): la app sigue sin cola

export const usePending = () =>
  useSyncExternalStore(
    (l) => {
      listeners.add(l)
      return () => listeners.delete(l)
    },
    () => snapshot,
  )

export async function enqueue(body: TransactionBody, id: string) {
  await queueDb.pending.put({ id, body, createdAt: Date.now() })
  await refresh()
}

export async function discard(id: string) {
  await queueDb.pending.delete(id)
  await refresh()
}

/**
 * Crea un movimiento. Si no hay red (fetch lanza TypeError) lo guarda en la cola con el MISMO id
 * del intento: si el servidor sí lo recibió y solo se perdió la respuesta, el reintento no duplica.
 * Los errores del servidor (4xx/5xx) no se encolan: el usuario debe verlos.
 */
export async function createTransaction(body: TransactionBody): Promise<'sent' | 'queued'> {
  const id = crypto.randomUUID()
  try {
    await api('/transactions', { method: 'POST', body: { ...body, id } })
    return 'sent'
  } catch (e) {
    if (!(e instanceof TypeError)) throw e
    await enqueue(body, id)
    return 'queued'
  }
}

let inflight: Promise<number> | null = null

/** Envía lo pendiente en orden. Devuelve cuántos se enviaron. Seguro de llamar varias veces. */
export function flushQueue(): Promise<number> {
  inflight ??= run().finally(() => (inflight = null))
  return inflight
}

async function run(): Promise<number> {
  let sent = 0
  for (const p of (await getPending()).filter((p) => !p.error)) {
    try {
      await api('/transactions', { method: 'POST', body: { ...p.body, id: p.id } })
      await queueDb.pending.delete(p.id)
      sent++
    } catch (e) {
      const rejected = e instanceof ApiError && e.status >= 400 && e.status < 500 && e.status !== 401 && e.status !== 429
      if (!rejected) break // sin red, sesión vencida o servidor caído: se reintenta más tarde, en orden
      await queueDb.pending.update(p.id, { error: e.message })
    }
  }
  await refresh()
  return sent
}
