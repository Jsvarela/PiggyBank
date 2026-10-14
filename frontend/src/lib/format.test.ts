import { expect, test } from 'vitest'
import { formatDate, formatMonth } from './format'
import { formatCOP } from './money'

test('mes y fecha legibles en español', () => {
  expect(formatMonth('2026-10')).toBe('octubre 2026')
  expect(formatMonth('2027-01')).toBe('enero 2027')
  expect(formatDate('2026-10-13')).toBe('13 oct 2026')
  expect(formatDate('2026-03-01')).toBe('1 mar 2026')
})

test('el monto usa espacio de no separación: nunca se parte entre $ y el número', () => {
  expect(formatCOP(1234567)).toBe('$ 1.234.567')
  expect(formatCOP(-12500)).toBe('-$ 12.500')
})
