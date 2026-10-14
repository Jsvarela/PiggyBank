import { afterEach, expect, test, vi } from 'vitest'
import { reportError } from './errorReporting'

afterEach(() => vi.unstubAllGlobals())

test('envía el error al servidor con mensaje, pila y ruta (sin datos de la persona)', async () => {
  const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
  vi.stubGlobal('fetch', fetchMock)
  await reportError(new Error('boom'))
  const [url, init] = fetchMock.mock.calls[0]
  expect(url).toBe('/api/client-errors')
  const body = JSON.parse(init.body)
  expect(body.message).toContain('boom')
  expect(body.stack).toContain('Error')
  expect(body.url).toBe(location.pathname) // solo la ruta: sin query ni montos
})

test('acepta cualquier cosa lanzada (texto, objeto) y recorta lo largo', async () => {
  const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
  vi.stubGlobal('fetch', fetchMock)
  await reportError('x'.repeat(5000))
  expect(JSON.parse(fetchMock.mock.calls[0][1].body).message.length).toBeLessThanOrEqual(2000)
})

test('si el reporte falla no lanza (un error al reportar no debe causar otro)', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('sin red')))
  await expect(reportError(new Error('x'))).resolves.toBeUndefined()
})

test('no reporta lo mismo dos veces seguidas', async () => {
  const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
  vi.stubGlobal('fetch', fetchMock)
  await reportError(new Error('repetido'))
  await reportError(new Error('repetido'))
  expect(fetchMock).toHaveBeenCalledTimes(1)
})
