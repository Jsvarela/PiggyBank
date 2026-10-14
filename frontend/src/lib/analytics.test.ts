import { beforeEach, expect, test, vi } from 'vitest'
import { initAnalytics, trackPage } from './analytics'

beforeEach(() => {
  document.head.innerHTML = ''
  delete (window as { goatcounter?: unknown }).goatcounter
})

test('sin configurar no instala nada', () => {
  initAnalytics(null)
  expect(document.querySelector('script[data-goatcounter]')).toBeNull()
})

test('configurada, instala GoatCounter una sola vez y desactiva el conteo automático', () => {
  initAnalytics('https://yo.goatcounter.com/count')
  initAnalytics('https://yo.goatcounter.com/count')
  const scripts = document.querySelectorAll('script[data-goatcounter]')
  expect(scripts).toHaveLength(1)
  expect(scripts[0].getAttribute('data-goatcounter')).toBe('https://yo.goatcounter.com/count')
  expect(JSON.parse(scripts[0].getAttribute('data-goatcounter-settings')!)).toMatchObject({ no_onload: true })
})

test('solo acepta direcciones https', () => {
  initAnalytics('javascript:alert(1)')
  initAnalytics('http://inseguro.example/count')
  expect(document.querySelector('script[data-goatcounter]')).toBeNull()
})

test('cada cambio de pantalla cuenta solo la ruta, nunca parámetros', () => {
  const count = vi.fn()
  ;(window as { goatcounter?: unknown }).goatcounter = { count }
  trackPage('/presupuestos')
  expect(count).toHaveBeenCalledWith({ path: '/presupuestos' })
  trackPage('/restablecer?token=secreto')
  expect(count).toHaveBeenLastCalledWith({ path: '/restablecer' })
})
