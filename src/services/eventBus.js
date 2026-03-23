const listeners = new Map()

export function emitEvent(name, payload) {
  const callbacks = listeners.get(name) || new Set()
  callbacks.forEach((callback) => callback({ payload }))
}

export async function listenEvent(name, callback) {
  if (!listeners.has(name)) {
    listeners.set(name, new Set())
  }
  listeners.get(name).add(callback)
  return () => {
    listeners.get(name)?.delete(callback)
  }
}
