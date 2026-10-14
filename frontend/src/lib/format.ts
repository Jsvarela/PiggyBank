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
