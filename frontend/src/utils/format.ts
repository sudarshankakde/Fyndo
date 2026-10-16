/**
 * Pure formatters using standard Intl APIs for currency, distance, and numbers.
 */

const inrFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
})

export function formatRupees(amount: number): string {
  if (isNaN(amount)) return '₹0'
  return inrFormatter.format(amount)
}

export function formatDistance(meters: number): string {
  if (meters < 1000) {
    return `${Math.round(meters)} m away`
  }
  const km = (meters / 1000).toFixed(1)
  return `${km} km away`
}

export function formatDiscount(type: string, value: number): string {
  if (type === 'PERCENTAGE') {
    return `${Math.round(value)}% OFF`
  }
  if (type === 'FLAT_AMOUNT') {
    return `${formatRupees(value)} OFF`
  }
  if (type === 'BOGO') {
    return 'Buy 1 Get 1'
  }
  return `${value}`
}

export function formatTimeRemaining(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs < 10 ? '0' : ''}${secs}`
}
