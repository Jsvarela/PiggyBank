import { expect, test } from 'vitest'
import { isDark, nextMode } from './theme'

test('automático sigue al sistema; claro y oscuro lo ignoran', () => {
  expect(isDark('system', true)).toBe(true)
  expect(isDark('system', false)).toBe(false)
  expect(isDark('light', true)).toBe(false)
  expect(isDark('dark', false)).toBe(true)
})

test('el botón recorre automático -> claro -> oscuro', () => {
  expect(nextMode('system')).toBe('light')
  expect(nextMode('light')).toBe('dark')
  expect(nextMode('dark')).toBe('system')
})
