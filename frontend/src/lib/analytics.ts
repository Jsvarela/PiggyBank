// Analítica opcional con GoatCounter (gratis para uso personal, sin cookies). Está apagada hasta que el
// servidor define ANALYTICS_URL. Solo se envía la ruta de cada pantalla (/presupuestos): nunca montos,
// descripciones ni parámetros de la dirección.
type GoatCounter = { count: (opts: { path: string }) => void }

export function initAnalytics(url: string | null) {
  if (!url?.startsWith('https://') || document.querySelector('script[data-goatcounter]')) return
  const s = document.createElement('script')
  s.async = true
  s.src = 'https://gc.zgo.at/count.js'
  s.dataset.goatcounter = url
  s.dataset.goatcounterSettings = JSON.stringify({ no_onload: true }) // en una SPA se cuenta a mano
  document.head.appendChild(s)
}

export function trackPage(pathname: string) {
  const gc = (window as { goatcounter?: GoatCounter }).goatcounter
  gc?.count({ path: pathname.split('?')[0] })
}
