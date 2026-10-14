// Los montos son enteros en COP (sin decimales). Formato: "$ 1.234.567".
// El espacio es "de no separación" para que el monto nunca se parta en dos líneas.
export function formatCOP(amount: number): string {
  const sign = amount < 0 ? '-' : ''
  const digits = Math.abs(amount).toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.')
  return `${sign}$ ${digits}`
}

// Igual que MAX_MONEY del servidor (backend/app/schemas.py): 15 cifras, exacto en JavaScript.
export const MAX_MONEY = 999_999_999_999_999
export const MONEY_TOO_BIG = 'Monto demasiado grande (máximo $ 999.999.999.999.999)'
