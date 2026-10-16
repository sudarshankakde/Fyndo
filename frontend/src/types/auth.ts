import { SupportedLanguage } from './api'

export type UserRole = 'SHOPPER' | 'MERCHANT' | 'SUPER_ADMIN' | 'ROLE_CASHIER'

export interface UserProfile {
  id: string
  phone: string
  full_name?: string | null
  email?: string | null
  role: UserRole
  preferred_language: SupportedLanguage
  merchant_id?: string | null
  business_name?: string | null
  kyc_status?: string | null
}

export interface AuthSession {
  accessToken: string
  refreshToken?: string
  user: UserProfile
}

export interface StaffSession {
  accessToken: string
  refreshToken?: string
  staffId: string
  staffName: string
  merchantId: string
  businessName: string
}

export interface AdminLoginPayload {
  identifier: string
  password: string
  mfa_code?: string
}

export interface RefreshTokenResponseData {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface UserProfileUpdatePayload {
  full_name?: string
  email?: string
  preferred_language?: SupportedLanguage
}
