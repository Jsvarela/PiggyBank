import { expect, test } from 'vitest'
import { ApiError } from '../api/client'
import { authView } from './authView'

const user = { id: 1, email: 'a@b.co', email_verified: true }
const base = { user: undefined, isLoading: false, error: null, hadSession: true }

test('con sesión válida entra a la app', () => {
  expect(authView({ ...base, user })).toBe('app')
})

test('mientras consulta, espera (no muestra el login)', () => {
  expect(authView({ ...base, isLoading: true })).toBe('loading')
})

test('solo un 401 de verdad te lleva al login', () => {
  expect(authView({ ...base, error: new ApiError(401, 'No autenticado') })).toBe('login')
})

test('servidor gratuito dormido (502/503/504) NO te saca de la sesión', () => {
  for (const status of [500, 502, 503, 504]) {
    expect(authView({ ...base, error: new ApiError(status, 'x') })).toBe('app')
  }
})

test('sin internet tampoco te saca de la sesión', () => {
  expect(authView({ ...base, error: new TypeError('sin red') })).toBe('app')
})

test('sin historial de sesión (primera vez) un fallo del servidor muestra el login', () => {
  expect(authView({ ...base, hadSession: false, error: new ApiError(503, 'x') })).toBe('login')
  expect(authView({ ...base, hadSession: false })).toBe('login')
})
