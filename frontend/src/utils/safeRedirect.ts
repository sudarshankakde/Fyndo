/**
 * Validates post-login redirect targets to prevent open redirect vulnerabilities.
 * Target must be a relative URL starting with single '/' and not '//'.
 */
export function getSafeRedirect(target: string | null | undefined, fallback: string = '/'): string {
  if (!target) return fallback
  const trimmed = target.trim()
  if (trimmed.startsWith('/') && !trimmed.startsWith('//') && !trimmed.startsWith('/\\')) {
    return trimmed
  }
  return fallback
}
