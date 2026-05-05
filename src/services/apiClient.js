import { clearAuthState, getAuthToken } from './authState.js'

const DEFAULT_BASE = import.meta?.env?.VITE_API_BASE_URL || ''

function withQuery(path, query) {
  if (!query || Object.keys(query).length === 0) return path
  const search = new URLSearchParams()
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      search.set(key, String(value))
    }
  })
  const queryString = search.toString()
  return queryString ? `${path}?${queryString}` : path
}

async function request(path, { method = 'GET', body, formData, query } = {}) {
  const url = `${DEFAULT_BASE}${withQuery(path, query)}`
  const options = { method, headers: {} }
  const authToken = getAuthToken()

  if (authToken) {
    options.headers.Authorization = `Bearer ${authToken}`
  }

  if (formData) {
    options.body = formData
  } else if (body !== undefined) {
    options.headers['Content-Type'] = 'application/json'
    options.body = JSON.stringify(body)
  }

  const response = await fetch(url, options)
  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json')
    ? await response.json().catch(() => null)
    : await response.text().catch(() => '')

  if (!response.ok) {
    if (response.status === 401 && path !== '/api/auth/login') {
      clearAuthState()
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
        const redirect = encodeURIComponent(`${window.location.pathname}${window.location.search}`)
        window.location.replace(`/login?redirect=${redirect}`)
      }
    }
    const message = typeof payload === 'string'
      ? payload
      : payload?.error || payload?.message || payload?.detail || response.statusText
    throw new Error(message || 'Request failed')
  }

  return payload
}

export const apiClient = {
  get(path, query) {
    return request(path, { method: 'GET', query })
  },
  post(path, body) {
    return request(path, { method: 'POST', body })
  },
  put(path, body) {
    return request(path, { method: 'PUT', body })
  },
  delete(path) {
    return request(path, { method: 'DELETE' })
  },
  upload(path, formData) {
    return request(path, { method: 'POST', formData })
  },
  uploadWithProgress(path, formData, onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      const url = `${DEFAULT_BASE}${path}`
      xhr.open('POST', url)
      xhr.timeout = 120000
      const authToken = getAuthToken()
      if (authToken) {
        xhr.setRequestHeader('Authorization', `Bearer ${authToken}`)
      }
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable && onProgress) {
          onProgress({ loaded: e.loaded, total: e.total, percent: Math.round((e.loaded / e.total) * 100) })
        }
      }
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try { resolve(JSON.parse(xhr.responseText)) }
          catch { resolve(xhr.responseText) }
        } else {
          let message = xhr.statusText || 'Upload failed'
          try {
            const payload = JSON.parse(xhr.responseText)
            message = payload?.error || payload?.message || payload?.detail || message
          } catch {}
          reject(new Error(message))
        }
      }
      xhr.onerror = () => {
        reject(new Error(`Upload failed (network/xhr): status=${xhr.status}, readyState=${xhr.readyState}, url=${url}`))
      }
      xhr.ontimeout = () => {
        reject(new Error(`Upload timeout after ${xhr.timeout}ms: url=${url}`))
      }
      xhr.onabort = () => {
        reject(new Error(`Upload aborted: url=${url}`))
      }
      xhr.send(formData)
    })
  },
  open(path, query) {
    const authToken = getAuthToken()
    const finalQuery = authToken
      ? { ...(query || {}), authToken }
      : query
    window.open(`${DEFAULT_BASE}${withQuery(path, finalQuery)}`, '_blank', 'noopener,noreferrer')
  },
  download(path, query) {
    const authToken = getAuthToken()
    const finalQuery = {
      ...(query || {}),
      ...(authToken ? { authToken } : {}),
      _ts: Date.now(),
    }
    const href = `${DEFAULT_BASE}${withQuery(path, finalQuery)}`
    const link = document.createElement('a')
    link.href = href
    link.style.display = 'none'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }
}
