import { useEffect, useState } from 'react'

interface InstallEvent extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: string }>
}

const isStandalone = () =>
  window.matchMedia('(display-mode: standalone)').matches || (navigator as { standalone?: boolean }).standalone === true
// iPhone/iPad: Safari no ofrece botón de instalar, solo "Agregar a pantalla de inicio"
const isIos = () => /iphone|ipad|ipod/i.test(navigator.userAgent)

export default function InstallApp() {
  const [event, setEvent] = useState<InstallEvent | null>(null)

  useEffect(() => {
    const onPrompt = (e: Event) => {
      e.preventDefault()
      setEvent(e as InstallEvent)
    }
    window.addEventListener('beforeinstallprompt', onPrompt)
    return () => window.removeEventListener('beforeinstallprompt', onPrompt)
  }, [])

  return (
    <section className="rounded-xl bg-surface p-4 shadow-sm">
      <h2 className="mb-1 font-medium">Instalar app</h2>
      {isStandalone() ? (
        <p className="text-sm text-slate-600">Ya estás usando la app instalada.</p>
      ) : event ? (
        <button
          className="w-full rounded-lg bg-brand py-2 text-white"
          onClick={() => {
            event.prompt()
            setEvent(null)
          }}
        >
          Instalar en este dispositivo
        </button>
      ) : isIos() ? (
        <p className="text-sm text-slate-600">
          En Safari toca el botón Compartir y elige <b>Agregar a pantalla de inicio</b>. Solo funciona desde Safari.
        </p>
      ) : (
        <p className="text-sm text-slate-600">
          En Chrome abre el menú ⋮ y elige <b>Instalar app</b> (si no aparece, usa HTTPS y recarga la página).
        </p>
      )}
    </section>
  )
}
