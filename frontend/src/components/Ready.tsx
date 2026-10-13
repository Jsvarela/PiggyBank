import type { ReactNode } from 'react'

/**
 * Los formularios fijan sus valores iniciales al montarse. Si las listas que usan (cuentas,
 * categorías) aún no cargaron, el campo queda vacío aunque el selector muestre la primera
 * opción. Por eso se montan solo cuando los datos ya están.
 */
export default function Ready({ of, children }: { of: { isSuccess: boolean; isError: boolean }[]; children: ReactNode }) {
  if (of.some((q) => q.isError)) return <p className="text-sm text-red-600">No se pudieron cargar los datos.</p>
  if (!of.every((q) => q.isSuccess)) return <p className="text-sm text-slate-500">Cargando…</p>
  return <>{children}</>
}
