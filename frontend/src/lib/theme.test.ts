import { expect, test } from 'vitest'
import { isDark, nextMode, themeColor } from './theme'

test('la barra de estado toma el color de la cabecera, no el de la marca', () => {
  expect(themeColor(false)).toBe('#ffffff') // igual que --color-surface en claro
  expect(themeColor(true)).toBe('#1e293b') // y en oscuro
})

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
