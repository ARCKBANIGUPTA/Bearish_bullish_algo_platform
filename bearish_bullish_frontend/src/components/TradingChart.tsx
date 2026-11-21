import {
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  LineStyle,
  createChart,
  type CandlestickData,
  type IChartApi,
  type IPriceLine,
  type ISeriesApi,
  type Time,
} from 'lightweight-charts'
import { useEffect, useRef, useState } from 'react'
import { fetchCandles, isAbortError } from '../services/api'
import { formatDate, formatPct, formatPrice } from '../format'
import { useScreenerStore } from '../store'
import type { CandleResponse, Signal } from '../types'

const COLORS = {
  bg: '#020617',
  grid: '#1e293b',
  text: '#94a3b8',
  up: '#10b981',
  down: '#f43f5e',
  ltp: '#e2e8f0',
}

const SIGNAL_BADGE: Record<Signal, string> = {
  BULLISH: 'bg-emerald-500/20 text-emerald-300',
  BEARISH: 'bg-rose-500/20 text-rose-300',
  NEUTRAL: 'bg-slate-700 text-slate-300',
}

interface FetchState {
  key: string
  data?: CandleResponse
  error?: string
}

export function TradingChart() {
  const symbol = useScreenerStore((s) => s.selectedSymbol)
  const lastScanAt = useScreenerStore((s) => s.lastScanAt)

  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const priceLinesRef = useRef<IPriceLine[]>([])
  const fittedSymbolRef = useRef<string | null>(null)

  const [retry, setRetry] = useState(0)
  const [state, setState] = useState<FetchState>({ key: '' })

  // Re-fetch on symbol change, on every new scan (keeps today's candle live) and on retry.
  const requestKey = symbol ? `${symbol}|${lastScanAt ?? ''}|${retry}` : ''
  const loading = !!symbol && state.key !== requestKey
  const data = state.data && state.data.symbol === symbol ? state.data : undefined

  // ---- create the chart once
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const chart = createChart(el, {
      autoSize: true,
      layout: { background: { type: ColorType.Solid, color: COLORS.bg }, textColor: COLORS.text },
      grid: { vertLines: { color: COLORS.grid }, horzLines: { color: COLORS.grid } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: COLORS.grid },
      timeScale: { borderColor: COLORS.grid, rightOffset: 4, barSpacing: 10 },
    })
    seriesRef.current = chart.addSeries(CandlestickSeries, {
      upColor: COLORS.up,
      downColor: COLORS.down,
      wickUpColor: COLORS.up,
      wickDownColor: COLORS.down,
      borderVisible: false,
    })
    chartRef.current = chart
    return () => {
      chart.remove()
      chartRef.current = null
      seriesRef.current = null
      priceLinesRef.current = []
      fittedSymbolRef.current = null
    }
  }, [])

  // ---- fetch candles (aborts the in-flight request when the symbol changes)
  useEffect(() => {
    if (!symbol) return
    const key = `${symbol}|${lastScanAt ?? ''}|${retry}`
    const controller = new AbortController()
    fetchCandles(symbol, controller.signal)
      .then((res) => setState({ key, data: res }))
      .catch((err: unknown) => {
        if (isAbortError(err)) return
        setState({ key, error: err instanceof Error ? err.message : 'Failed to load candles' })
      })
    return () => controller.abort()
  }, [symbol, lastScanAt, retry])

  // ---- push data + breakout levels into the chart
  useEffect(() => {
    const series = seriesRef.current
    const chart = chartRef.current
    if (!series || !chart) return

    for (const line of priceLinesRef.current) series.removePriceLine(line)
    priceLinesRef.current = []

    if (!data) {
      if (!symbol) series.setData([])
      return
    }

    const bars: CandlestickData<Time>[] = data.candles.map((c) => ({
      time: c.time as Time,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }))
    series.setData(bars)

    const sig = data.signal
    if (sig) {
      priceLinesRef.current = [
        series.createPriceLine({
          price: sig.high_5d, color: COLORS.up, lineWidth: 1, lineStyle: LineStyle.Dashed,
          axisLabelVisible: true, title: `${data.lookback_days}D High`,
        }),
        series.createPriceLine({
          price: sig.low_5d, color: COLORS.down, lineWidth: 1, lineStyle: LineStyle.Dashed,
          axisLabelVisible: true, title: `${data.lookback_days}D Low`,
        }),
        series.createPriceLine({
          price: sig.ltp, color: COLORS.ltp, lineWidth: 1, lineStyle: LineStyle.Dotted,
          axisLabelVisible: true, title: 'LTP',
        }),
      ]
    }

    // Only reset the viewport when switching symbols, not on periodic refreshes.
    if (fittedSymbolRef.current !== data.symbol) {
      chart.timeScale().fitContent()
      fittedSymbolRef.current = data.symbol
    }
  }, [data, symbol])

  const sig = data?.signal ?? null
  const error = state.key === requestKey ? state.error : undefined

  return (
    <section className="flex min-h-0 min-w-0 flex-1 flex-col bg-slate-950">
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 border-b border-slate-800 px-4 py-2">
        <h2 className="text-lg font-semibold text-slate-100">{symbol ?? 'Select a symbol'}</h2>
        {sig && (
          <>
            <span className={`rounded px-2 py-0.5 text-xs font-semibold ${SIGNAL_BADGE[sig.signal]}`}>
              {sig.signal}
            </span>
            <span className="text-sm tabular-nums text-slate-200">
              LTP {formatPrice(sig.ltp)}{' '}
              <span className={sig.change_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                {formatPct(sig.change_pct)}
              </span>
            </span>
            <span className="text-xs tabular-nums text-slate-400">
              {data?.lookback_days}D range{' '}
              <span className="text-rose-300">{formatPrice(sig.low_5d)}</span> –{' '}
              <span className="text-emerald-300">{formatPrice(sig.high_5d)}</span>
            </span>
            {sig.signal !== 'NEUTRAL' && (
              <span className="text-xs text-slate-400">breakout {formatPct(sig.breakout_pct, false)}</span>
            )}
          </>
        )}
        <span className="ml-auto text-xs text-slate-500">
          Daily · session {formatDate(data?.session_date ?? null)}
        </span>
      </div>

      <div className="relative min-h-0 flex-1">
        <div ref={containerRef} className="absolute inset-0" />

        {!symbol && (
          <Overlay>Pick a stock from the screener to plot its daily chart.</Overlay>
        )}
        {symbol && loading && !data && <Overlay><Spinner /> Loading {symbol}…</Overlay>}
        {symbol && error && (
          <Overlay>
            <div className="flex max-w-md flex-col items-center gap-3 text-center">
              <p className="text-rose-300">Couldn’t load {symbol}</p>
              <p className="text-xs text-slate-400">{error}</p>
              <button
                type="button"
                onClick={() => setRetry((n) => n + 1)}
                className="rounded-md bg-slate-800 px-3 py-1.5 text-sm text-slate-200 hover:bg-slate-700"
              >
                Retry
              </button>
            </div>
          </Overlay>
        )}

        {data && (
          <div className="pointer-events-none absolute left-3 top-3 z-10 flex gap-3 rounded bg-slate-900/80 px-2 py-1 text-[11px] text-slate-300">
            <Legend color={COLORS.up} label={`${data.lookback_days}D High`} dashed />
            <Legend color={COLORS.down} label={`${data.lookback_days}D Low`} dashed />
            <Legend color={COLORS.ltp} label="LTP" dashed />
          </div>
        )}
      </div>
    </section>
  )
}

function Overlay({ children }: { children: React.ReactNode }) {
  return (
    <div className="absolute inset-0 z-20 flex items-center justify-center gap-2 bg-slate-950/70 text-sm text-slate-400">
      {children}
    </div>
  )
}

function Spinner() {
  return <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-600 border-t-slate-200" aria-hidden />
}

function Legend({ color, label, dashed }: { color: string; label: string; dashed?: boolean }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="inline-block w-4 border-t-2" style={{ borderColor: color, borderStyle: dashed ? 'dashed' : 'solid' }} />
      {label}
    </span>
  )
}
