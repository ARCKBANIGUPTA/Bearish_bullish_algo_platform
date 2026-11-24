// Mirrors bearish_bullish_backend/models.py – keep in sync.
// JSDoc typedefs only (no runtime code); editors use them for autocomplete.

/** @typedef {'BULLISH' | 'BEARISH' | 'NEUTRAL'} Signal */
/** @typedef {'groww' | 'mock'} DataSource */

/**
 * @typedef {Object} SignalResult
 * @property {string} symbol
 * @property {Signal} signal
 * @property {number} ltp
 * @property {number} high_5d       Highest high of the previous N completed sessions
 * @property {number} low_5d        Lowest low of the previous N completed sessions
 * @property {number} prev_close
 * @property {number} change_pct    LTP vs previous session close, %
 * @property {number} breakout_pct  Distance beyond the broken level, % (0 when NEUTRAL)
 * @property {string} session_date
 */

/**
 * @typedef {Object} ScreenerSnapshot
 * @property {SignalResult[]} bullish
 * @property {SignalResult[]} bearish
 * @property {number} neutral_count
 * @property {string[]} failed
 * @property {number} universe_size
 * @property {number} lookback_days
 * @property {string} session_date
 * @property {string} scanned_at
 * @property {string | null} next_scan_at
 * @property {number} duration_ms
 * @property {DataSource} data_source
 */

/**
 * @typedef {Object} DailyCandle
 * @property {string} time  Session date, YYYY-MM-DD
 * @property {number} open
 * @property {number} high
 * @property {number} low
 * @property {number} close
 * @property {number | null} volume
 */

/**
 * @typedef {Object} CandleResponse
 * @property {string} symbol
 * @property {'1d'} interval
 * @property {DailyCandle[]} candles
 * @property {number} lookback_days
 * @property {string} session_date
 * @property {SignalResult | null} signal
 */

/**
 * @typedef {{ type: 'screener_update', data: ScreenerSnapshot }
 *   | { type: 'scan_error', message: string, at: string }} WsMessage
 */

/** @typedef {'connecting' | 'open' | 'closed'} WsStatus */

export {}
