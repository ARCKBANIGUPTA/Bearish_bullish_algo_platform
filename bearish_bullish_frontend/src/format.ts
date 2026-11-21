const priceFmt = new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

export const formatPrice = (n: number): string => priceFmt.format(n)

export const formatPct = (n: number, signed = true): string =>
  `${signed && n > 0 ? '+' : ''}${n.toFixed(2)}%`

export function formatTime(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleTimeString('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Asia/Kolkata',
  })
}

export function formatDate(isoDate: string | null): string {
  if (!isoDate) return '—'
  const d = new Date(`${isoDate}T00:00:00+05:30`)
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', weekday: 'short', timeZone: 'Asia/Kolkata' })
}
