// Los montos son enteros en COP (sin decimales). Formato: "$ 1.234.567".
export function formatCOP(amount: number): string {
  const sign = amount < 0 ? '-' : ''
  const digits = Math.abs(amount).toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.')
  return `${sign}$ ${digits}`
}
