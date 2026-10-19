import { env } from '@/config/env'

/**
 * Validates external media URLs to avoid loading unverified remote resources.
 */
export function isSafeMediaUrl(url: string | null | undefined): boolean {
  if (!url) return false
  try {
    const parsed = new URL(url)
    if (parsed.protocol !== 'https:') return false
    return env.mediaHosts.some(
      (host: string) => parsed.hostname === host || parsed.hostname.endsWith(`.${host}`)
    )
  } catch {
    return false
  }
}

export function getSafeMediaUrl(url: string | null | undefined, fallback: string = ''): string {
  return isSafeMediaUrl(url) ? (url as string) : fallback
}
