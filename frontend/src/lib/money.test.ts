import { expect, test } from 'vitest'
import { formatCOP } from './money'

test('formatea pesos colombianos', () => {
  expect(formatCOP(1234567)).toBe('$ 1.234.567')
  expect(formatCOP(0)).toBe('$ 0')
  expect(formatCOP(-50000)).toBe('-$ 50.000')
})
