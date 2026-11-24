const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''
const DEFAULT_TIMEOUT_MS = 15_000

export class ApiError extends Error {
  /**
   * @param {string} message
   * @param {number} status  HTTP status (0 = network/timeout)
   * @param {number | null} [retryAfterSec]
   */
  constructor(message, status, retryAfterSec = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.retryAfterSec = retryAfterSec
  }
}

/** @param {Response} res @returns {Promise<string>} */
async function readDetail(res) {
  try {
    const body = await res.json()
    if (body && typeof body === 'object' && 'detail' in body) {
      return typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    }
  } catch {
    /* non-JSON error body */
  }
  return res.statusText || `HTTP ${res.status}`
}

/** @param {string} path @param {AbortSignal} [signal] */
async function getJson(path, signal) {
  const timeout = AbortSignal.timeout(DEFAULT_TIMEOUT_MS)
  const combined = signal ? AbortSignal.any([signal, timeout]) : timeout

  let res
  try {
    res = await fetch(`${API_BASE}${path}`, {
      headers: { Accept: 'application/json' },
      signal: combined,
    })
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err // caller cancelled
    if (err instanceof DOMException && err.name === 'TimeoutError') {
      throw new ApiError('Request timed out', 0)
    }
    throw new ApiError('Backend unreachable – is the FastAPI server running on :8000?', 0)
  }

  if (!res.ok) {
    const retryAfter = res.headers.get('Retry-After')
    throw new ApiError(await readDetail(res), res.status, retryAfter ? Number(retryAfter) : null)
  }
  return res.json()
}

/**
 * @param {string} symbol
 * @param {AbortSignal} [signal]
 * @returns {Promise<import('../types').CandleResponse>}
 */
export function fetchCandles(symbol, signal) {
  return getJson(`/api/candles/${encodeURIComponent(symbol)}`, signal)
}

/**
 * @param {AbortSignal} [signal]
 * @returns {Promise<import('../types').ScreenerSnapshot>}
 */
export function fetchScreener(signal) {
  return getJson('/api/screener', signal)
}

/** @param {unknown} err */
export function isAbortError(err) {
  return err instanceof DOMException && err.name === 'AbortError'
}
