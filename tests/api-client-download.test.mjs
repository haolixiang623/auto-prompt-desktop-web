import test from 'node:test'
import assert from 'node:assert/strict'

function createStorageMock() {
  const store = new Map()
  return {
    getItem(key) {
      return store.has(key) ? store.get(key) : null
    },
    setItem(key, value) {
      store.set(key, String(value))
    },
    removeItem(key) {
      store.delete(key)
    },
    clear() {
      store.clear()
    },
  }
}

function installDom() {
  const localStorage = createStorageMock()
  const sessionStorage = createStorageMock()
  const clickedLinks = []
  const appendedNodes = []

  globalThis.window = {
    localStorage,
    sessionStorage,
    location: {
      pathname: '/',
      search: '',
      replace() {},
    },
  }

  globalThis.document = {
    body: {
      appendChild(node) {
        appendedNodes.push(node)
      },
      removeChild(node) {
        const index = appendedNodes.indexOf(node)
        if (index >= 0) {
          appendedNodes.splice(index, 1)
        }
      },
    },
    createElement(tag) {
      if (tag === 'a') {
        return {
          href: '',
          style: {},
          click() {
            clickedLinks.push(this.href)
          },
        }
      }
      return { style: {}, content: {} }
    },
  }

  return { clickedLinks, localStorage, sessionStorage }
}

function cleanupDom() {
  delete globalThis.window
  delete globalThis.document
}

async function loadModules() {
  const suffix = `test=${Date.now()}-${Math.random()}`
  const auth = await import(`../src/services/authState.js?${suffix}`)
  const api = await import(`../src/services/apiClient.js?${suffix}`)
  return { auth, api }
}

test('apiClient.download appends auth token and cache-busting timestamp', async () => {
  const originalNow = Date.now
  Date.now = () => 1_777_776_000_000
  const { clickedLinks } = installDom()
  const { auth, api } = await loadModules()

  auth.setAuthSession(
    {
      token: 'remember-token',
      expiresAt: '2030-01-01T00:00:00',
      user: { id: 'user-1', username: 'alice', role: 'user' },
    },
    { rememberMe: true },
  )

  api.apiClient.download('/api/files/download', { path: '/tmp/factors.xlsx' })

  assert.equal(clickedLinks.length, 1)
  const href = clickedLinks[0]
  assert.match(href, /^\/api\/files\/download\?/)
  assert.match(href, /path=%2Ftmp%2Ffactors\.xlsx/)
  assert.match(href, /authToken=remember-token/)
  assert.match(href, /_ts=1777776000000/)

  cleanupDom()
  Date.now = originalNow
})
