// Los montos son enteros en COP (sin decimales). Formato: "$ 1.234.567".
// El espacio es "de no separación" para que el monto nunca se parta en dos líneas.
export function formatCOP(amount: number): string {
  const sign = amount < 0 ? '-' : ''
  const digits = Math.abs(amount).toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.')
  return `${sign}$ ${digits}`
}
