const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']

/** '2026-10' -> 'octubre 2026' */
export function formatMonth(ym: string): string {
  const [y, m] = ym.split('-')
  return `${MESES[Number(m) - 1]} ${y}`
}

/** '2026-10-13' -> '13 oct 2026' (se arma a mano: sin zonas horarias que corran el día) */
export function formatDate(iso: string): string {
  const [y, m, d] = iso.split('-')
  return `${Number(d)} ${MESES[Number(m) - 1].slice(0, 3)} ${y}`
}

/** Porcentajes de presupuesto: por encima de 999 solo importa que se pasó, no por cuánto. */
export const formatPercent = (p: number) => (p > 999 ? '>999%' : `${p}%`)

/** `plural(1, 'día', 'días')` -> '1 día'; `plural(2, 'día', 'días')` -> '2 días' */
export const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`
