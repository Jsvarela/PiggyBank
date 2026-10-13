import { createContext, useContext } from 'react'
import type { Transaction } from '../api/types'

/** Abre el formulario de movimiento: sin argumento crea uno nuevo, con uno lo edita. */
export const EditorContext = createContext<(tx?: Transaction) => void>(() => {})
export const useEditor = () => useContext(EditorContext)
