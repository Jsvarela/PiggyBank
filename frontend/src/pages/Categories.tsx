import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { useApiMutation, useCategories } from '../api/hooks'
import type { Category, CategoryBody } from '../api/types'
import Ready from '../components/Ready'

const schema = z.object({
  name: z.string().trim().min(1, 'Escribe un nombre'),
  kind: z.enum(['income', 'expense']),
  parent_id: z.number().nullable(),
  archived: z.boolean(),
})

function CategoryForm({ category, onDone }: { category?: Category; onDone: () => void }) {
  const parents = (useCategories().data ?? []).filter((c) => c.parent_id === null && c.id !== category?.id)
  const save = useApiMutation<CategoryBody>(category ? 'PUT' : 'POST', () => (category ? `/categories/${category.id}` : '/categories'))
  const del = useApiMutation<number>('DELETE', (id) => `/categories/${id}`)
  const { register, handleSubmit, formState } = useForm<CategoryBody>({
    resolver: zodResolver(schema),
    defaultValues: category ?? { name: '', kind: 'expense', parent_id: null, archived: false },
  })

  return (
    <form onSubmit={handleSubmit((v) => save.mutate(v, { onSuccess: onDone }))} className="space-y-2 rounded-xl bg-surface p-4 shadow-sm">
      <input placeholder="Nombre" className="w-full rounded-lg border border-slate-300 p-2" {...register('name')} />
      {formState.errors.name && <p className="text-sm text-red-600">{formState.errors.name.message}</p>}
      <select className="w-full rounded-lg border border-slate-300 p-2" {...register('kind')}>
        <option value="expense">Gasto</option>
        <option value="income">Ingreso</option>
      </select>
      <select className="w-full rounded-lg border border-slate-300 p-2" {...register('parent_id', { setValueAs: (v) => (v ? Number(v) : null) })}>
        <option value="">Sin categoría padre</option>
        {parents.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
          </option>
        ))}
      </select>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" {...register('archived')} /> Archivada
      </label>
      {(save.error || del.error) && <p className="text-sm text-red-600">{(save.error ?? del.error)?.message}</p>}
      <div className="flex gap-2">
        <button type="button" className="rounded-lg border px-4 py-2" onClick={onDone}>
          Cancelar
        </button>
        {category && (
          <button type="button" className="rounded-lg border border-red-300 px-4 py-2 text-red-700" onClick={() => confirm('¿Borrar la categoría?') && del.mutate(category.id, { onSuccess: onDone })}>
            Borrar
          </button>
        )}
        <button className="flex-1 rounded-lg bg-brand py-2 text-white">Guardar</button>
      </div>
    </form>
  )
}

export default function Categories() {
  const query = useCategories()
  const categories = query.data ?? []
  const [editing, setEditing] = useState<Category | null | undefined>(undefined)

  if (editing !== undefined)
    return (
      <Ready of={[query]}>
        <CategoryForm key={editing?.id ?? 'new'} category={editing ?? undefined} onDone={() => setEditing(undefined)} />
      </Ready>
    )
  return (
    <div className="space-y-3">
      <button className="w-full rounded-lg bg-brand py-2 text-white" onClick={() => setEditing(null)}>
        Nueva categoría
      </button>
      <ul className="divide-y rounded-xl bg-surface px-4 shadow-sm">
        {categories.map((c) => (
          <li key={c.id}>
            <button className="flex w-full justify-between py-3 text-left" onClick={() => setEditing(c)}>
              <span>
                {c.parent_id ? '↳ ' : ''}
                {c.name}
                {c.archived && <span className="text-xs text-slate-500"> · archivada</span>}
              </span>
              <span className="text-xs text-slate-500">{c.kind === 'income' ? 'Ingreso' : 'Gasto'}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
