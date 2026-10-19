import { CURRENCY } from './config'

const money = new Intl.NumberFormat(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const day = new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short', year: 'numeric' })

export const formatMoney = (n) => `${CURRENCY} ${money.format(Number(n) || 0)}`

// Parse YYYY-MM-DD as a local date so it never shifts a day across time zones.
export function formatDate(iso) {
  const [y, m, d] = iso.split('-').map(Number)
  return day.format(new Date(y, m - 1, d))
}

export function todayIso() {
  const now = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
}
