import { useState } from 'react'
import { formatPct, formatPrice } from '../format'
import { useScreenerStore } from '../store'

/** @typedef {'bullish' | 'bearish'} Tab */

const TABS = /** @type {const} */ (['bullish', 'bearish'])

const TAB_STYLE = {
  bullish: {
    label: 'Bullish (CE Targets)',
    active: 'border-emerald-400 text-emerald-300',
    badge: 'bg-emerald-500/20 text-emerald-300',
    accent: 'text-emerald-400',
  },
  bearish: {
    label: 'Bearish (PE Targets)',
    active: 'border-rose-400 text-rose-300',
    badge: 'bg-rose-500/20 text-rose-300',
    accent: 'text-rose-400',
  },
}

/**
 * @param {{
 *   item: import('../types').SignalResult,
 *   tab: Tab,
 *   selected: boolean,
 *   onSelect: (symbol: string) => void,
 * }} props
 */
function Row({ item, tab, selected, onSelect }) {
  const level = tab === 'bullish' ? item.high_5d : item.low_5d
  return (
    <li>
      <button
        type="button"
        onClick={() => onSelect(item.symbol)}
        aria-current={selected}
        className={`grid w-full grid-cols-[1fr_auto] gap-x-3 px-3 py-2 text-left text-sm transition-colors hover:bg-slate-800/70 ${
          selected ? 'bg-slate-800 ring-1 ring-inset ring-slate-600' : ''
        }`}
      >
        <span className="truncate font-medium text-slate-100">{item.symbol}</span>
        <span className="text-right tabular-nums text-slate-200">{formatPrice(item.ltp)}</span>
        <span className="text-xs text-slate-500">
          {tab === 'bullish' ? '5D H' : '5D L'} {formatPrice(level)}
          <span className={`ml-2 ${TAB_STYLE[tab].accent}`}>
            {tab === 'bullish' ? '▲' : '▼'} {formatPct(item.breakout_pct, false)}
          </span>
        </span>
        <span className={`text-right text-xs tabular-nums ${item.change_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
          {formatPct(item.change_pct)}
        </span>
      </button>
    </li>
  )
}

export function ScreenerList() {
  const bullish = useScreenerStore((s) => s.bullish)
  const bearish = useScreenerStore((s) => s.bearish)
  const lastScanAt = useScreenerStore((s) => s.lastScanAt)
  const selected = useScreenerStore((s) => s.selectedSymbol)
  const selectSymbol = useScreenerStore((s) => s.selectSymbol)
  const [tab, setTab] = useState(/** @type {Tab} */ ('bullish'))
  const [query, setQuery] = useState('')

  const items = tab === 'bullish' ? bullish : bearish
  const q = query.trim().toUpperCase()
  const visible = q ? items.filter((i) => i.symbol.includes(q)) : items

  return (
    <aside className="flex w-full shrink-0 flex-col border-r border-slate-800 bg-slate-900 md:w-80">
      <div className="grid grid-cols-2 border-b border-slate-800" role="tablist">
        {TABS.map((t) => {
          const count = t === 'bullish' ? bullish.length : bearish.length
          const active = tab === t
          return (
            <button
              key={t}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => setTab(t)}
              className={`flex items-center justify-center gap-2 border-b-2 px-2 py-2.5 text-xs font-semibold transition-colors ${
                active ? TAB_STYLE[t].active : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              {TAB_STYLE[t].label}
              <span className={`rounded px-1.5 py-0.5 text-[10px] ${TAB_STYLE[t].badge}`}>{count}</span>
            </button>
          )
        })}
      </div>

      <div className="border-b border-slate-800 p-2">
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Filter symbol…"
          aria-label="Filter symbols"
          className="w-full rounded-md border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-sm text-slate-100 placeholder:text-slate-500 focus:border-slate-500 focus:outline-none"
        />
      </div>

      <ul className="min-h-0 flex-1 divide-y divide-slate-800/60 overflow-y-auto">
        {lastScanAt === null ? (
          <li className="p-6 text-center text-sm text-slate-500">Waiting for the first scan…</li>
        ) : visible.length === 0 ? (
          <li className="p-6 text-center text-sm text-slate-500">
            {q ? `No match for “${query}”` : `No ${tab} breakouts right now`}
          </li>
        ) : (
          visible.map((item) => (
            <Row key={item.symbol} item={item} tab={tab} selected={item.symbol === selected} onSelect={selectSymbol} />
          ))
        )}
      </ul>
    </aside>
  )
}
