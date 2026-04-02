import { ensureWindowDropBridge } from '../services/uploadService.js'
import { listenEvent } from '../services/eventBus.js'

export async function listen(name, callback) {
  ensureWindowDropBridge()
  return listenEvent(name, callback)
}
