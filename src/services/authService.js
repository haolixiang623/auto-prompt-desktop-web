import { apiClient } from './apiClient.js'
import {
  authState,
  clearAuthState,
  getAuthToken,
  hasAuthSession,
  isAdminUser,
  setAuthSession,
  setCurrentUser
} from './authState.js'

let authLoadPromise = null

export { authState, hasAuthSession, isAdminUser }

export async function ensureAuthLoaded() {
  if (authState.ready) return authState
  if (authLoadPromise) return authLoadPromise

  const token = getAuthToken()
  if (!token) {
    authState.ready = true
    return authState
  }

  authState.loading = true
  authLoadPromise = apiClient.get('/api/auth/me')
    .then((user) => {
      setCurrentUser(user)
      return authState
    })
    .catch(() => {
      clearAuthState()
      return authState
    })
    .finally(() => {
      authState.loading = false
      authState.ready = true
      authLoadPromise = null
    })

  return authLoadPromise
}

export async function login(username, password) {
  const session = await apiClient.post('/api/auth/login', { username, password })
  setAuthSession(session)
  return session
}

export async function logout() {
  try {
    if (getAuthToken()) {
      await apiClient.post('/api/auth/logout', {})
    }
  } catch {
    // Ignore logout failures and clear client state anyway.
  }

  clearAuthState()
}
