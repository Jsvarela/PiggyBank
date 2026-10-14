// Los montos son enteros en COP (sin decimales). Formato: "$ 1.234.567".
// El espacio es "de no separación" para que el monto nunca se parta en dos líneas.
export function formatCOP(amount: number): string {
  const sign = amount < 0 ? '-' : ''
  const digits = Math.abs(amount).toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.')
  return `${sign}$ ${digits}`
}

// Botones de suma rápida del registro: toque a toque se arma el monto sin teclear.
export const QUICK_AMOUNTS = [1_000, 5_000, 10_000, 20_000, 50_000, 100_000]

/** Suma `inc` al monto actual (vacío = 0). Siempre entero, entre 0 y MAX_MONEY. */
export function addToAmount(current: number | undefined, inc: number): number {
  const base = Number.isFinite(current) ? Math.floor(current as number) : 0
  return Math.min(Math.max(base + inc, 0), MAX_MONEY)
}

// Igual que MAX_MONEY del servidor (backend/app/schemas.py): 15 cifras, exacto en JavaScript.
export const MAX_MONEY = 999_999_999_999_999
export const MONEY_TOO_BIG = 'Monto demasiado grande (máximo $ 999.999.999.999.999)'
