import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type {
  Account,
  BudgetStatus,
  Category,
  Dashboard,
  MonthlyReport,
  Transaction,
  TransactionFilters,
  User,
} from './types'

export const useMe = () => useQuery({ queryKey: ['me'], queryFn: () => api<User>('/auth/me'), retry: false })
export const useAccounts = () => useQuery({ queryKey: ['accounts'], queryFn: () => api<Account[]>('/accounts') })
export const useCategories = () =>
  useQuery({ queryKey: ['categories'], queryFn: () => api<Category[]>('/categories') })
export const useDashboard = () => useQuery({ queryKey: ['dashboard'], queryFn: () => api<Dashboard>('/dashboard') })

export function useTransactions(f: TransactionFilters) {
  const params = new URLSearchParams()
  for (const [k, v] of Object.entries(f)) if (v !== undefined && v !== '') params.set(k, String(v))
  return useQuery({
    queryKey: ['transactions', f],
    queryFn: () => api<{ items: Transaction[]; total: number }>(`/transactions?${params}`),
    placeholderData: (prev) => prev,
  })
}

/** Cualquier cambio invalida todo: son pocos datos y así los saldos nunca quedan viejos. */
export function useApiMutation<B = void>(method: string, path: (body: B) => string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: B) => api(path(body), { method, body: method === 'DELETE' ? undefined : body }),
    onSuccess: () => qc.invalidateQueries(),
  })
}

export const useBudgetStatus = (month?: string) =>
  useQuery({ queryKey: ['budget-status', month], queryFn: () => api<BudgetStatus[]>(`/budgets/status${month ? `?month=${month}` : ''}`) })
export const useMonthlyReport = (month: string) =>
  useQuery({ queryKey: ['monthly-report', month], queryFn: () => api<MonthlyReport>(`/reports/monthly?month=${month}`) })
