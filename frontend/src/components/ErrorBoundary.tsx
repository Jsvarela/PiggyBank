import { Component, type ReactNode } from 'react'
import { reportError } from '../lib/errorReporting'

/** Si un componente falla al dibujarse, en vez de una pantalla en blanco se muestra esto. */
export default class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  componentDidCatch(error: Error) {
    void reportError(error)
  }

  render() {
    if (!this.state.failed) return this.props.children
    return (
      <div className="mx-auto mt-16 max-w-sm space-y-3 p-4 text-center">
        <h1 className="text-xl font-semibold">Algo salió mal</h1>
        <p className="text-sm text-slate-600">Ocurrió un error inesperado. Tus datos están a salvo. Recarga la página para continuar.</p>
        <button className="rounded-lg bg-brand px-4 py-2 text-white" onClick={() => location.assign('/')}>
          Volver al inicio
        </button>
      </div>
    )
  }
}
