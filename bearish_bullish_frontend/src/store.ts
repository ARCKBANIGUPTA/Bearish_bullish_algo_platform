import { create } from 'zustand'
import type { DataSource, ScreenerSnapshot, SignalResult, WsStatus } from './types'

interface ScreenerState {
  wsStatus: WsStatus
  bullish: SignalResult[]
  bearish: SignalResult[]
  neutralCount: number
  failedCount: number
  universeSize: number
  lookbackDays: number
  sessionDate: string | null
  lastScanAt: string | null
  nextScanAt: string | null
  dataSource: DataSource | null
  scanError: string | null
  selectedSymbol: string | null

  setWsStatus: (status: WsStatus) => void
  setSnapshot: (snapshot: ScreenerSnapshot) => void
  setScanError: (message: string | null) => void
  selectSymbol: (symbol: string) => void
}

export const useScreenerStore = create<ScreenerState>()((set, get) => ({
  wsStatus: 'connecting',
  bullish: [],
  bearish: [],
  neutralCount: 0,
  failedCount: 0,
  universeSize: 0,
  lookbackDays: 5,
  sessionDate: null,
  lastScanAt: null,
  nextScanAt: null,
  dataSource: null,
  scanError: null,
  selectedSymbol: null,

  setWsStatus: (wsStatus) => set({ wsStatus }),

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

  setScanError: (scanError) => set({ scanError }),

  selectSymbol: (selectedSymbol) => set({ selectedSymbol }),
}))
