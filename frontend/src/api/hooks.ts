import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { setSession, readCache, writeCache } from '../lib/localCache'
import { ApiError, api } from './client'
import type {
  Account,
  BudgetStatus,
  Category,
  Dashboard,
  Goal,
  MonthlyReport,
  RecurringRule,
  Transaction,
  TransactionFilters,
  UpcomingPayment,
  User,
} from './types'

export const useMe = () =>
  useQuery({
    queryKey: ['me'],
    // un 401 es definitivo; cualquier otro fallo (servidor dormido, sin red) se reintenta ~25 s mientras despierta
    retry: (n, e) => !(e instanceof ApiError && e.status === 401) && n < 6,
    retryDelay: 4000,
    queryFn: async () => {
      try {
        const user = await api<User>('/auth/me')
        setSession(true)
        return user
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) setSession(false)
        throw e
      }
    },
  })

/** Lista con copia local: sin red se usa la última conocida (y se sigue pidiendo al servidor). */
const useCachedList = <T>(key: string, path: string) =>
  useQuery({
    queryKey: [key],
    queryFn: async () => {
      const data = await api<T[]>(path)
      writeCache(key, data)
      return data
    },
    initialData: () => readCache<T[]>(key),
    initialDataUpdatedAt: 0, // la copia local se considera vieja: igual se refresca al montar
  })
export const useAccounts = () => useCachedList<Account>('accounts', '/accounts')
export const useCategories = () => useCachedList<Category>('categories', '/categories')
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

export const useRecurring = () => useQuery({ queryKey: ['recurring'], queryFn: () => api<RecurringRule[]>('/recurring') })
export const useUpcoming = (days = 30) =>
  useQuery({ queryKey: ['upcoming', days], queryFn: () => api<UpcomingPayment[]>(`/recurring/upcoming?days=${days}`) })
export const useGoals = () => useQuery({ queryKey: ['goals'], queryFn: () => api<Goal[]>('/savings-goals') })

export const useConfig = () =>
  useQuery({
    queryKey: ['config'],
    queryFn: () => api<{ email_enabled: boolean; analytics_url: string | null }>('/config'),
    staleTime: Infinity,
  })
