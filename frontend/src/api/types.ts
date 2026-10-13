export type AccountType = 'cash' | 'bank' | 'digital_wallet' | 'credit_card' | 'savings'
export type TxType = 'income' | 'expense' | 'transfer'

export const ACCOUNT_TYPES: Record<AccountType, string> = {
  cash: 'Efectivo',
  bank: 'Banco',
  digital_wallet: 'Billetera digital',
  credit_card: 'Tarjeta de crÃ©dito',
  savings: 'Ahorros',
}

export const TX_TYPES: Record<TxType, string> = {
  expense: 'Gasto',
  income: 'Ingreso',
  transfer: 'Transferencia',
}

export interface User {
  id: number
  email: string
}

export interface AccountBody {
  name: string
  type: AccountType
  initial_balance: number
  archived: boolean
}
export interface Account extends AccountBody {
  id: number
  balance: number
}

export interface CategoryBody {
  name: string
  kind: 'income' | 'expense'
  parent_id: number | null
  archived: boolean
}
export interface Category extends CategoryBody {
  id: number
}

export interface TransactionBody {
  type: TxType
  amount: number
  date: string
  account_id: number
  to_account_id: number | null
  category_id: number | null
  description: string | null
}
export interface Transaction extends TransactionBody {
  id: string
  tags: string[]
  recurring_rule_id?: number | null
  goal_id?: number | null
}

export interface Dashboard {
  month: string
  accounts: Account[]
  net_worth: number
  income: number
  expense: number
  recent: Transaction[]
}

export interface TransactionFilters {
  from?: string
  to?: string
  account_id?: number
  category_id?: number
  type?: TxType
  q?: string
  limit: number
  offset: number
}

export interface BudgetStatus {
  budget_id: number
  category_id: number
  category_name: string
  is_default: boolean
  limit: number
  alert_threshold: number
  spent: number
  percent: number
  remaining: number
  alert: 'ok' | 'warning' | 'exceeded'
  days_left: number
}

export interface BudgetBody {
  category_id: number
  month: string | null
  limit_amount: number
  alert_threshold: number
}

export interface MonthlyReport {
  month: string
  income: number
  expense: number
  previous_income: number
  previous_expense: number
  categories: { category_id: number; name: string; amount: number; previous: number; diff: number }[]
}

export type Frequency = 'daily' | 'weekly' | 'biweekly' | 'monthly' | 'yearly'
export const FREQUENCIES: Record<Frequency, string> = {
  daily: 'Diaria',
  weekly: 'Semanal',
  biweekly: 'Cada 14 días',
  monthly: 'Mensual',
  yearly: 'Anual',
}

export interface RecurringBody {
  type: TxType
  amount: number
  account_id: number
  to_account_id: number | null
  category_id: number | null
  description: string | null
  frequency: Frequency
  start_date: string
  end_date: string | null
  active: boolean
}
export interface RecurringRule extends RecurringBody {
  id: number
  next_run_date: string
}

export interface UpcomingPayment {
  rule_id: number
  date: string
  type: TxType
  amount: number
  description: string | null
  account_id: number
  to_account_id: number | null
  category_id: number | null
}

export interface GoalBody {
  name: string
  target_amount: number
  deadline: string | null
  account_id: number | null
}
export interface Goal extends GoalBody {
  id: number
  saved: number
  remaining: number
  percent: number
  reached: boolean
  monthly_suggested: number | null
}
