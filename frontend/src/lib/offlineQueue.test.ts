import 'fake-indexeddb/auto'
import { beforeEach, expect, test, vi } from 'vitest'
import type { TransactionBody } from '../api/types'
import { createTransaction, discard, enqueue, flushQueue, getPending, queueDb } from './offlineQueue'

const body = (amount: number): TransactionBody => ({
  type: 'expense', amount, date: '2026-10-13', account_id: 1, to_account_id: null, category_id: 1, description: null,
})
const reply = (status: number, json: unknown = {}) => new Response(JSON.stringify(json), { status })
const sentIds = (fetchMock: ReturnType<typeof vi.fn>) => fetchMock.mock.calls.map((c) => JSON.parse(c[1].body).id)

beforeEach(async () => {
  await queueDb.pending.clear()
  vi.unstubAllGlobals()
})

test('al volver la conexión envía lo pendiente en orden, con su id, y vacía la cola', async () => {
  await enqueue(body(1), 'a')
  await enqueue(body(2), 'b')
  const fetchMock = vi.fn().mockImplementation(async () => reply(201))
  vi.stubGlobal('fetch', fetchMock)
  expect(await flushQueue()).toBe(2)
  expect(sentIds(fetchMock)).toEqual(['a', 'b'])
  expect(await getPending()).toEqual([])
})

test('sin red se queda en la cola y no sigue intentando con el resto', async () => {
  await enqueue(body(1), 'a')
  await enqueue(body(2), 'b')
  const fetchMock = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'))
  vi.stubGlobal('fetch', fetchMock)
  expect(await flushQueue()).toBe(0)
  expect(fetchMock).toHaveBeenCalledTimes(1)
  expect((await getPending()).map((p) => p.id)).toEqual(['a', 'b'])
})

test('un movimiento rechazado (4xx) se marca con error y los demás igual se envían', async () => {
  await enqueue(body(1), 'a')
  await enqueue(body(2), 'b')
  vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(reply(404, { detail: 'La cuenta no existe' })).mockResolvedValueOnce(reply(201)))
  expect(await flushQueue()).toBe(1)
  const left = await getPending()
  expect(left).toHaveLength(1)
  expect(left[0]).toMatchObject({ id: 'a', error: 'La cuenta no existe' })
  // lo fallido no se reintenta solo
  const again = vi.fn()
  vi.stubGlobal('fetch', again)
  await flushQueue()
  expect(again).not.toHaveBeenCalled()
})

test('sesión vencida (401) no descarta nada: queda pendiente', async () => {
  await enqueue(body(1), 'a')
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(reply(401, { detail: 'No autenticado' })))
  expect(await flushQueue()).toBe(0)
  const left = await getPending()
  expect(left.map((p) => p.id)).toEqual(['a'])
  expect(left[0].error).toBeUndefined() // sigue elegible para reintento
})

test('dos sincronizaciones simultáneas no envían dos veces', async () => {
  await enqueue(body(1), 'a')
  const fetchMock = vi.fn().mockImplementation(async () => reply(201))
  vi.stubGlobal('fetch', fetchMock)
  await Promise.all([flushQueue(), flushQueue()])
  expect(fetchMock).toHaveBeenCalledTimes(1)
})

test('crear con red envía directo; sin red encola con el MISMO id del intento', async () => {
  const ok = vi.fn().mockResolvedValue(reply(201))
  vi.stubGlobal('fetch', ok)
  expect(await createTransaction(body(5))).toBe('sent')
  expect(await getPending()).toEqual([])

  const down = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'))
  vi.stubGlobal('fetch', down)
  expect(await createTransaction(body(6))).toBe('queued')
  const [pending] = await getPending()
  // si el servidor sí recibió el primer intento, el reintento es idempotente porque el id coincide
  expect(sentIds(down)).toEqual([pending.id])
})

test('un error del servidor al crear NO se encola: se muestra', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(reply(422, { detail: 'Categoría inválida' })))
  await expect(createTransaction(body(1))).rejects.toThrow('Categoría inválida')
  expect(await getPending()).toEqual([])
})

test('descartar quita el movimiento de la cola', async () => {
  await enqueue(body(1), 'a')
  await discard('a')
  expect(await getPending()).toEqual([])
})
