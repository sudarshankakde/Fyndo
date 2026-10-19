export interface ResponseEnvelope<T> {
  success: boolean
  data: T
  message?: string
  error?: {
    code: string
    message: string
    details?: unknown[]
  }
}

export type SupportedLanguage = 'en' | 'hi' | 'mr'

export type SectorType = 'FOOD' | 'FASHION' | 'FOOTWEAR' | 'ELECTRONICS' | 'REAL_ESTATE'
