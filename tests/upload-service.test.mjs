import test from 'node:test'
import assert from 'node:assert/strict'

function createLocalStorageMock() {
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
    }
  }
}

function createEnvironment(mockFile, tracker) {
  const windowListeners = new Map()
  const genericElement = {
    style: {},
    appendChild() {},
    setAttribute() {},
    removeAttribute() {},
    remove() {},
    content: {},
  }

  const windowMock = {
    localStorage: createLocalStorageMock(),
    setTimeout,
    clearTimeout,
    addEventListener(type, handler) {
      windowListeners.set(type, handler)
    },
    removeEventListener(type) {
      windowListeners.delete(type)
    },
    showDirectoryPicker: async () => {
      tracker.showDirectoryPickerCalled = true
      return {
        name: 'workspace',
        async *values() {}
      }
    }
  }

  const documentMock = {
    body: {
      appendChild() {},
    },
    createElement(tag) {
      if (tag !== 'input') {
        return { ...genericElement }
      }
      const listeners = new Map()
      return {
        type: 'file',
        multiple: false,
        accept: '',
        style: {},
        files: [],
        webkitdirectory: false,
        setAttribute() {},
        addEventListener(type, handler) {
          listeners.set(type, handler)
        },
        remove() {},
        showPicker() {
          tracker.showPickerCalled = true
          this.files = [mockFile]
          listeners.get('change')?.()
        },
        click() {
          tracker.inputClickCalled = true
          this.files = [mockFile]
          listeners.get('change')?.()
        }
      }
    }
  }

  return { windowMock, documentMock }
}

test('selectWorkspace uses input-based directory picker instead of showDirectoryPicker', async () => {
  const mockFile = new File(
    ['mock workbook'],
    'factors.xlsx',
    { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' },
  )
  Object.defineProperty(mockFile, 'webkitRelativePath', {
    value: 'workspace/factors.xlsx',
    configurable: true,
  })
  const tracker = {
    showDirectoryPickerCalled: false,
    showPickerCalled: false,
    inputClickCalled: false,
  }

  const { windowMock, documentMock } = createEnvironment(mockFile, tracker)
  globalThis.window = windowMock
  globalThis.document = documentMock
  globalThis.fetch = async () => ({
    ok: true,
    headers: new Headers({ 'content-type': 'application/json' }),
    json: async () => ({ rootPath: '/uploaded/workspace', id: 'ws-1' }),
    text: async () => '',
  })

  const { selectWorkspace } = await import(`../src/services/uploadService.js?test=${Date.now()}`)
  const result = await selectWorkspace()

  assert.deepEqual(result, { rootPath: '/uploaded/workspace', id: 'ws-1' })
  assert.equal(tracker.showDirectoryPickerCalled, false)
  assert.equal(tracker.showPickerCalled || tracker.inputClickCalled, true)

  delete globalThis.window
  delete globalThis.document
  delete globalThis.fetch
})
