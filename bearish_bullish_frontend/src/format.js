const priceFmt = new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

/** @param {number} n */
export const formatPrice = (n) => priceFmt.format(n)

/** @param {number} n @param {boolean} [signed] */
export const formatPct = (n, signed = true) => `${signed && n > 0 ? '+' : ''}${n.toFixed(2)}%`

/** @param {string | null} iso */
export function formatTime(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleTimeString('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Asia/Kolkata',
  })
}

/** @param {string | null} isoDate */
export function formatDate(isoDate) {
  if (!isoDate) return '—'
  const d = new Date(`${isoDate}T00:00:00+05:30`)
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', weekday: 'short', timeZone: 'Asia/Kolkata' })
}
