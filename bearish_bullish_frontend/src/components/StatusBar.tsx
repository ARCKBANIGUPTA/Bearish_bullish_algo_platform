import { formatDate, formatTime } from '../format'
import { useScreenerStore } from '../store'
import type { WsStatus } from '../types'

const STATUS_STYLE: Record<WsStatus, { dot: string; label: string }> = {
  open: { dot: 'bg-emerald-400', label: 'Live' },
  connecting: { dot: 'bg-amber-400 animate-pulse', label: 'Connecting…' },
  closed: { dot: 'bg-rose-500', label: 'Disconnected – retrying' },
}

export function StatusBar() {
  const wsStatus = useScreenerStore((s) => s.wsStatus)
  const lastScanAt = useScreenerStore((s) => s.lastScanAt)
  const nextScanAt = useScreenerStore((s) => s.nextScanAt)
  const sessionDate = useScreenerStore((s) => s.sessionDate)
  const universeSize = useScreenerStore((s) => s.universeSize)
  const neutral = useScreenerStore((s) => s.neutralCount)
  const failed = useScreenerStore((s) => s.failedCount)
  const lookback = useScreenerStore((s) => s.lookbackDays)
  const dataSource = useScreenerStore((s) => s.dataSource)
  const scanError = useScreenerStore((s) => s.scanError)
  const status = STATUS_STYLE[wsStatus]

  return (
    <header className="shrink-0 border-b border-slate-800 bg-slate-900/80">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-1 px-4 py-2 text-xs text-slate-400">
        <h1 className="text-sm font-semibold tracking-wide text-slate-100">
          F&amp;O {lookback}-Day Breakout Screener
        </h1>
        <span className="flex items-center gap-2">
          <span className={`h-2 w-2 rounded-full ${status.dot}`} aria-hidden />
          {status.label}
        </span>
        <span>Session: <b className="text-slate-200">{formatDate(sessionDate)}</b></span>
        <span>Last scan: <b className="text-slate-200">{formatTime(lastScanAt)}</b></span>
        <span>Next scan: <b className="text-slate-200">{formatTime(nextScanAt)}</b></span>
        <span>
          Universe <b className="text-slate-200">{universeSize}</b> · neutral {neutral}
          {failed > 0 && <> · <span className="text-amber-400">{failed} no data</span></>}
        </span>
        <span className="ml-auto text-slate-500">Observation only · not investment advice</span>
      </div>
      {dataSource === 'mock' && (
        <div className="bg-amber-500/15 px-4 py-1 text-center text-xs font-medium text-amber-300">
          DEMO DATA – synthetic prices (DATA_SOURCE=mock). Not real market data.
        </div>
      )}
      {scanError && (
        <div role="alert" className="bg-rose-500/15 px-4 py-1 text-center text-xs text-rose-300">
          {scanError}
        </div>
      )}
    </header>
  )
}
