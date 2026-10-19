import { SupportedLanguage } from '@/types/api'

/**
 * Programmatically triggers Google Translate without exposing Google's default widget.
 * Preserves Fyndo's custom UI, design tokens, and trilingual pill styling.
 */
export function applyGoogleTranslation(targetLang: SupportedLanguage): void {
  if (typeof window === 'undefined') return

  const lang = targetLang.toLowerCase()

  if (lang === 'en') {
    // Clear Google translation cookies to restore original English
    document.cookie = 'googtrans=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;'
    document.cookie = `googtrans=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; domain=${window.location.hostname}`
  } else {
    const cookieValue = `/en/${lang}`
    document.cookie = `googtrans=${cookieValue}; path=/; domain=${window.location.hostname}`
    document.cookie = `googtrans=${cookieValue}; path=/`
  }

  const triggerChange = (): boolean => {
    const select = document.querySelector<HTMLSelectElement>('.goog-te-combo')
    if (select) {
      select.value = lang
      select.dispatchEvent(new Event('change'))
      return true
    }
    return false
  }

  if (!triggerChange()) {
    // If the Google script is still bootstrapping, retry briefly
    let attempts = 0
    const interval = setInterval(() => {
      attempts += 1
      if (triggerChange() || attempts > 20) {
        clearInterval(interval)
      }
    }, 200)
  }
}
