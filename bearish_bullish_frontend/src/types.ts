// Mirrors bearish_bullish_backend/models.py – keep in sync.

export type Signal = 'BULLISH' | 'BEARISH' | 'NEUTRAL'
export type DataSource = 'groww' | 'mock'

export interface SignalResult {
  symbol: string
  signal: Signal
  ltp: number
  /** Highest high of the previous N completed sessions */
  high_5d: number
  /** Lowest low of the previous N completed sessions */
  low_5d: number
  prev_close: number
  /** LTP vs previous session close, % */
  change_pct: number
  /** Distance beyond the broken level, % (0 when NEUTRAL) */
  breakout_pct: number
  session_date: string
}

export interface ScreenerSnapshot {
  bullish: SignalResult[]
  bearish: SignalResult[]
  neutral_count: number
  failed: string[]
  universe_size: number
  lookback_days: number
  session_date: string
  scanned_at: string
  next_scan_at: string | null
  duration_ms: number
  data_source: DataSource
}

export interface DailyCandle {
  /** Session date, YYYY-MM-DD */
  time: string
  open: number
  high: number
  low: number
  close: number
  volume: number | null
}

export interface CandleResponse {
  symbol: string
  interval: '1d'
  candles: DailyCandle[]
  lookback_days: number
  session_date: string
  signal: SignalResult | null
}

export interface ScreenerUpdateMessage {
  type: 'screener_update'
  data: ScreenerSnapshot
}

export interface ScanErrorMessage {
  type: 'scan_error'
  message: string
  at: string
}

export type WsMessage = ScreenerUpdateMessage | ScanErrorMessage

export type WsStatus = 'connecting' | 'open' | 'closed'
