/** Fecha de hoy (YYYY-MM-DD) en America/Bogota, igual que el backend. */
export function todayBogota(now = new Date()): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Bogota' }).format(now)
}
