import { useScreenerStore } from '../store'

const PING_INTERVAL_MS = 25_000
const MIN_BACKOFF_MS = 1_000
const MAX_BACKOFF_MS = 30_000

function defaultWsUrl() {
  const configured = import.meta.env.VITE_WS_URL
  if (configured) return configured
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/ws/screener`
}

/** @param {unknown} value @returns {value is import('../types').WsMessage} */
function isWsMessage(value) {
  if (!value || typeof value !== 'object' || !('type' in value)) return false
  const msg = /** @type {{ type: unknown, data?: any, message?: unknown }} */ (value)
  if (msg.type === 'screener_update') {
    const d = msg.data
    return !!d && Array.isArray(d.bullish) && Array.isArray(d.bearish)
  }
  return msg.type === 'scan_error' && typeof msg.message === 'string'
}

/** Screener WebSocket client with heartbeat and exponential-backoff reconnect. */
export class ScreenerSocket {
  /** @type {WebSocket | null} */
  #ws = null
  /** @type {ReturnType<typeof setInterval> | null} */
  #pingTimer = null
  /** @type {ReturnType<typeof setTimeout> | null} */
  #reconnectTimer = null
  #backoff = MIN_BACKOFF_MS
  #stopped = false
  #url

  /** @param {string} [url] */
  constructor(url = defaultWsUrl()) {
    this.#url = url
  }

  connect() {
    this.#stopped = false
    this.#open()
  }

  disconnect() {
    this.#stopped = true
    this.#clearTimers()
    if (this.#ws) {
      this.#ws.onclose = null
      this.#ws.close()
      this.#ws = null
    }
  }

  #open() {
    useScreenerStore.getState().setWsStatus('connecting')

    let ws
    try {
      ws = new WebSocket(this.#url)
    } catch (err) {
      console.error('WebSocket construction failed', err)
      this.#scheduleReconnect()
      return
    }
    this.#ws = ws

    ws.onopen = () => {
      this.#backoff = MIN_BACKOFF_MS
      useScreenerStore.getState().setWsStatus('open')
      this.#pingTimer = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send('ping')
      }, PING_INTERVAL_MS)
    }

    ws.onmessage = (event) => {
      if (event.data === 'pong') return
      let parsed
      try {
        parsed = JSON.parse(event.data)
      } catch {
        console.warn('Ignoring non-JSON WS message')
        return
      }
      if (!isWsMessage(parsed)) {
        console.warn('Ignoring malformed WS message', parsed)
        return
      }
      const s = useScreenerStore.getState()
      if (parsed.type === 'screener_update') s.setSnapshot(parsed.data)
      else s.setScanError(parsed.message)
    }

    ws.onerror = () => {
      // onclose always follows; reconnect is handled there.
    }

    ws.onclose = () => {
      this.#clearTimers()
      this.#ws = null
      useScreenerStore.getState().setWsStatus('closed')
      if (!this.#stopped) this.#scheduleReconnect()
    }
  }

  #scheduleReconnect() {
    const jitter = Math.random() * 0.3 * this.#backoff
    const delay = Math.min(this.#backoff + jitter, MAX_BACKOFF_MS)
    this.#reconnectTimer = setTimeout(() => this.#open(), delay)
    this.#backoff = Math.min(this.#backoff * 2, MAX_BACKOFF_MS)
  }

  #clearTimers() {
    if (this.#pingTimer) clearInterval(this.#pingTimer)
    if (this.#reconnectTimer) clearTimeout(this.#reconnectTimer)
    this.#pingTimer = null
    this.#reconnectTimer = null
  }
}
