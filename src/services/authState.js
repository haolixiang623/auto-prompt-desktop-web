import { reactive } from 'vue'

const AUTH_TOKEN_KEY = 'auto-prompt.auth-token'
const AUTH_USER_KEY = 'auto-prompt.auth-user'
const AUTH_EXPIRY_KEY = 'auto-prompt.auth-expiry'
const REMEMBERED_USERNAME_KEY = 'auto-prompt.remembered-username'
const ONE_DAY_MS = 24 * 60 * 60 * 1000

function getStorage(kind) {
  if (typeof window === 'undefined') return null
  try {
    return kind === 'session'
      ? window.sessionStorage || null
      : window.localStorage || null
  } catch {
    return null
  }
}

function parseJson(value) {
  try {
    return value ? JSON.parse(value) : null
  } catch {
    return null
  }
}

function isExpired(expiresAt) {
  if (!expiresAt) return false
  const expiresAtMs = Date.parse(expiresAt)
  if (!Number.isFinite(expiresAtMs)) return false
  return expiresAtMs <= Date.now()
}

function clearAuthStorage(storage) {
  if (!storage) return
  storage.removeItem(AUTH_TOKEN_KEY)
  storage.removeItem(AUTH_USER_KEY)
  storage.removeItem(AUTH_EXPIRY_KEY)
}

function readSessionFromStorage(storage) {
  if (!storage) return null

  const token = storage.getItem(AUTH_TOKEN_KEY) || ''
  const user = parseJson(storage.getItem(AUTH_USER_KEY))
  const expiresAt = storage.getItem(AUTH_EXPIRY_KEY) || ''

  if (expiresAt && isExpired(expiresAt)) {
    clearAuthStorage(storage)
    return null
  }

  if (!token || !user) {
    return null
  }

  return {
    token,
    user,
    expiresAt,
    persistent: storage === getStorage('local')
  }
}

function readStoredSession() {
  const sessionStorage = getStorage('session')
  const localStorage = getStorage('local')
  return readSessionFromStorage(sessionStorage) || readSessionFromStorage(localStorage)
}

function readStoredUser() {
  return readStoredSession()?.user || null
}

function readStoredToken() {
  return readStoredSession()?.token || ''
}

function persistRememberedUsername(username) {
  const localStorage = getStorage('local')
  if (!localStorage) return

  if (!username) {
    localStorage.removeItem(REMEMBERED_USERNAME_KEY)
    return
  }

  localStorage.setItem(REMEMBERED_USERNAME_KEY, JSON.stringify({
    username,
    expiresAt: new Date(Date.now() + ONE_DAY_MS).toISOString()
  }))
}

function clearAllAuthStorage() {
  clearAuthStorage(getStorage('session'))
  clearAuthStorage(getStorage('local'))
}

const storedSession = readStoredSession()

export const authState = reactive({
  token: storedSession?.token || '',
  user: storedSession?.user || null,
  expiresAt: storedSession?.expiresAt || '',
  persistent: Boolean(storedSession?.persistent),
  ready: !storedSession?.token,
  loading: false
})

function persistAuthState() {
  clearAllAuthStorage()

  if (!authState.token || !authState.user) {
    return
  }

  const storage = getStorage(authState.persistent ? 'local' : 'session')
  if (!storage) return

  storage.setItem(AUTH_TOKEN_KEY, authState.token)
  storage.setItem(AUTH_USER_KEY, JSON.stringify(authState.user))
  if (authState.expiresAt) {
    storage.setItem(AUTH_EXPIRY_KEY, authState.expiresAt)
  }
}

export function getAuthToken() {
  if (authState.expiresAt && isExpired(authState.expiresAt)) {
    clearAuthState()
    return ''
  }
  return authState.token || readStoredToken()
}

export function setAuthSession(session, { rememberMe = false } = {}) {
  authState.token = session?.token || ''
  authState.user = session?.user || null
  authState.expiresAt = session?.expiresAt || ''
  authState.persistent = Boolean(rememberMe)
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
  authState.expiresAt = ''
  authState.persistent = false
  authState.ready = true
  authState.loading = false
  persistAuthState()
}

export function hasAuthSession() {
  if (authState.expiresAt && isExpired(authState.expiresAt)) {
    clearAuthState()
    return false
  }
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
  const localStorage = getStorage('local')
  if (!localStorage) return null
  return localStorage.getItem(getScopedStorageKey(baseKey))
}

export function setScopedStorageItem(baseKey, value) {
  const localStorage = getStorage('local')
  if (!localStorage) return
  localStorage.setItem(getScopedStorageKey(baseKey), value)
}

export function removeScopedStorageItem(baseKey) {
  const localStorage = getStorage('local')
  if (!localStorage) return
  localStorage.removeItem(getScopedStorageKey(baseKey))
}

export function getRememberedUsername() {
  const localStorage = getStorage('local')
  if (!localStorage) return ''

  const record = parseJson(localStorage.getItem(REMEMBERED_USERNAME_KEY))
  if (!record?.username) return ''
  if (isExpired(record.expiresAt)) {
    localStorage.removeItem(REMEMBERED_USERNAME_KEY)
    return ''
  }
  return record.username
}

export function setRememberedUsername(username) {
  persistRememberedUsername(String(username || '').trim())
}
