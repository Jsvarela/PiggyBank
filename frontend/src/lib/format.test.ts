import { expect, test } from 'vitest'
import { formatDate, formatMonth, formatPercent, plural } from './format'
import { MAX_MONEY, formatCOP } from './money'

test('porcentajes enormes se acotan: nadie necesita leer 1334567%', () => {
  expect(formatPercent(85)).toBe('85%')
  expect(formatPercent(999)).toBe('999%')
  expect(formatPercent(1000)).toBe('>999%')
  expect(formatPercent(1334567)).toBe('>999%')
})

test('plurales correctos: 1 día, 0 días, 2 días', () => {
  expect(plural(1, 'día', 'días')).toBe('1 día')
  expect(plural(0, 'día', 'días')).toBe('0 días')
  expect(plural(18, 'día restante', 'días restantes')).toBe('18 días restantes')
  expect(plural(1, 'movimiento', 'movimientos')).toBe('1 movimiento')
})

test('el tope de monto coincide con el del servidor y es exacto en JavaScript', () => {
  expect(MAX_MONEY).toBe(999_999_999_999_999)
  expect(MAX_MONEY).toBeLessThan(Number.MAX_SAFE_INTEGER)
  expect(formatCOP(MAX_MONEY)).toBe('$ 999.999.999.999.999')
})

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
