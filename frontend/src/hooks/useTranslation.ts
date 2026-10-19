import { useAppSelector } from '@/store'
import { translations } from '@/i18n/translations'

export function useTranslation() {
  const language = useAppSelector((state) => state.ui.language)
  const t = translations[language] || translations.en

  return { t, language }
}
