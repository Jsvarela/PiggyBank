import { expect, test } from 'vitest'
import { todayBogota } from './dates'

test('hoy se calcula en Bogotá, no en UTC', () => {
  // 03:00 UTC del 1 de marzo = 22:00 del 28 de febrero en Bogotá
  expect(todayBogota(new Date('2026-03-01T03:00:00Z'))).toBe('2026-02-28')
})
