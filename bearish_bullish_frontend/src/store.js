import { create } from 'zustand'

/** @typedef {import('./types').ScreenerSnapshot} ScreenerSnapshot */

export const useScreenerStore = create((set, get) => ({
  /** @type {import('./types').WsStatus} */
  wsStatus: 'connecting',
  /** @type {import('./types').SignalResult[]} */
  bullish: [],
  /** @type {import('./types').SignalResult[]} */
  bearish: [],
  neutralCount: 0,
  failedCount: 0,
  universeSize: 0,
  lookbackDays: 5,
  /** @type {string | null} */
  sessionDate: null,
  /** @type {string | null} */
  lastScanAt: null,
  /** @type {string | null} */
  nextScanAt: null,
  /** @type {import('./types').DataSource | null} */
  dataSource: null,
  /** @type {string | null} */
  scanError: null,
  /** @type {string | null} */
  selectedSymbol: null,

  setWsStatus: (wsStatus) => set({ wsStatus }),

  /** @param {ScreenerSnapshot} s */
  setSnapshot: (s) => {
    // Ignore stale snapshots (e.g. REST response arriving after a newer WS push).
    const current = get().lastScanAt
    if (current && Date.parse(s.scanned_at) < Date.parse(current)) return
    set({
      bullish: s.bullish,
      bearish: s.bearish,
      neutralCount: s.neutral_count,
      failedCount: s.failed.length,
      universeSize: s.universe_size,
      lookbackDays: s.lookback_days,
      sessionDate: s.session_date,
      lastScanAt: s.scanned_at,
      nextScanAt: s.next_scan_at,
      dataSource: s.data_source,
      scanError: null,
      // Auto-select the strongest breakout on first load.
      selectedSymbol: get().selectedSymbol ?? s.bullish[0]?.symbol ?? s.bearish[0]?.symbol ?? null,
    })
  },

  /** @param {string | null} scanError */
  setScanError: (scanError) => set({ scanError }),

  /** @param {string} selectedSymbol */
  selectSymbol: (selectedSymbol) => set({ selectedSymbol }),
}))
