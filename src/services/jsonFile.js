export function parseJsonFilePayload(payload) {
  if (typeof payload === 'string') {
    return JSON.parse(payload)
  }

  if (payload && typeof payload === 'object') {
    return payload
  }

  throw new TypeError('Unsupported JSON file payload')
}
