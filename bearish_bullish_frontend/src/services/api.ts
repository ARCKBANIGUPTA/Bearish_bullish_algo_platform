import type { CandleResponse, ScreenerSnapshot } from '../types'

const API_BASE: string = import.meta.env.VITE_API_BASE_URL ?? ''
const DEFAULT_TIMEOUT_MS = 15_000

export class ApiError extends Error {
  readonly status: number
  readonly retryAfterSec: number | null

  constructor(message: string, status: number, retryAfterSec: number | null = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.retryAfterSec = retryAfterSec
  }
}

async function readDetail(res: Response): Promise<string> {
  try {
    const body: unknown = await res.json()
    if (body && typeof body === 'object' && 'detail' in body) {
      const detail = (body as { detail: unknown }).detail
      if (typeof detail === 'string') return detail
      return JSON.stringify(detail)
    }
  } catch {
    /* non-JSON error body */
  }
  return res.statusText || `HTTP ${res.status}`
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const timeout = AbortSignal.timeout(DEFAULT_TIMEOUT_MS)
  const combined = signal ? AbortSignal.any([signal, timeout]) : timeout

  let res: Response
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
  return (await res.json()) as T
}

export function fetchCandles(symbol: string, signal?: AbortSignal): Promise<CandleResponse> {
  return getJson<CandleResponse>(`/api/candles/${encodeURIComponent(symbol)}`, signal)
}

export function fetchScreener(signal?: AbortSignal): Promise<ScreenerSnapshot> {
  return getJson<ScreenerSnapshot>('/api/screener', signal)
}

export function isAbortError(err: unknown): boolean {
  return err instanceof DOMException && err.name === 'AbortError'
}
