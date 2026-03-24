import { reactive } from 'vue'

const AUTH_TOKEN_KEY = 'auto-prompt.auth-token'
const AUTH_USER_KEY = 'auto-prompt.auth-user'

function readStoredUser() {
  if (typeof window === 'undefined') return null

  try {
    const raw = window.localStorage.getItem(AUTH_USER_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function readStoredToken() {
  if (typeof window === 'undefined') return ''
  return window.localStorage.getItem(AUTH_TOKEN_KEY) || ''
}

const storedUser = readStoredUser()
const storedToken = readStoredToken()

export const authState = reactive({
  token: storedToken,
  user: storedUser,
  ready: !storedToken,
  loading: false
})

function persistAuthState() {
  if (typeof window === 'undefined') return

  if (authState.token) {
    window.localStorage.setItem(AUTH_TOKEN_KEY, authState.token)
  } else {
    window.localStorage.removeItem(AUTH_TOKEN_KEY)
  }

  if (authState.user) {
    window.localStorage.setItem(AUTH_USER_KEY, JSON.stringify(authState.user))
  } else {
    window.localStorage.removeItem(AUTH_USER_KEY)
  }
}

export function getAuthToken() {
  return authState.token || readStoredToken()
}

export function setAuthSession(session) {
  authState.token = session?.token || ''
  authState.user = session?.user || null
  authState.ready = true
  persistAuthState()
}

export function setCurrentUser(user) {
  authState.user = user || null
  authState.ready = true
  persistAuthState()
}

export function clearAuthState() {
  authState.token = ''
  authState.user = null
  authState.ready = true
  authState.loading = false
  persistAuthState()
}

export function hasAuthSession() {
  return Boolean(authState.token && authState.user)
}

export function isAdminUser() {
  return authState.user?.role === 'admin'
}

export function getScopedStorageKey(baseKey) {
  const userId = authState.user?.id || readStoredUser()?.id
  return userId ? `${baseKey}:${userId}` : baseKey
}

export function getScopedStorageItem(baseKey) {
  if (typeof window === 'undefined') return null
  return window.localStorage.getItem(getScopedStorageKey(baseKey))
}

export function setScopedStorageItem(baseKey, value) {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(getScopedStorageKey(baseKey), value)
}

export function removeScopedStorageItem(baseKey) {
  if (typeof window === 'undefined') return
  window.localStorage.removeItem(getScopedStorageKey(baseKey))
}
