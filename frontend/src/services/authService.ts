import { http } from './http'
import { SupportedLanguage } from '@/types/api'
import {
  AdminLoginPayload,
  AuthSession,
  RefreshTokenResponseData,
  StaffSession,
  UserProfile,
  UserProfileUpdatePayload,
  UserRole,
} from '@/types/auth'

export interface OtpSendResult {
  phone: string
  expires_in_seconds: number
  test_otp?: string
}

interface BackendAuthTokenData {
  access_token: string
  refresh_token: string
  user: UserProfile
}

interface BackendStaffLoginData {
  access_token: string
  refresh_token?: string
  staff_id: string
  staff_name: string
  merchant_id: string
  business_name: string
}

export const authService = {
  async sendOtp(phone: string, channel: 'SMS' | 'WHATSAPP' = 'SMS'): Promise<OtpSendResult> {
    return http.post<any, OtpSendResult>('/auth/otp/send', { phone, channel })
  },

  async verifyOtp(
    phone: string,
    otp: string,
    preferredLanguage: SupportedLanguage = 'en'
  ): Promise<AuthSession> {
    const data = await http.post<any, BackendAuthTokenData>('/auth/otp/verify', {
      phone,
      otp,
      preferred_language: preferredLanguage,
    })
    return {
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      user: data.user,
    }
  },

  async staffLogin(storePhone: string, pin: string): Promise<StaffSession> {
    const data = await http.post<any, BackendStaffLoginData>('/auth/staff-login', {
      store_phone: storePhone,
      pin,
    })
    return {
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      staffId: data.staff_id,
      staffName: data.staff_name,
      merchantId: data.merchant_id,
      businessName: data.business_name,
    }
  },

  async adminLogin(payload: AdminLoginPayload): Promise<AuthSession> {
    const data = await http.post<any, BackendAuthTokenData>('/auth/admin-login', payload)
    return {
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      user: data.user,
    }
  },

  async refreshToken(refreshToken?: string): Promise<RefreshTokenResponseData> {
    return http.post<any, RefreshTokenResponseData>('/auth/refresh', {
      refresh_token: refreshToken || '',
    })
  },

  async logout(refreshToken?: string | null): Promise<void> {
    try {
      await http.post('/auth/logout', { refresh_token: refreshToken })
    } catch {
      // Best-effort server revocation
    }
  },

  async getMe(): Promise<UserProfile> {
    return http.get<any, UserProfile>('/auth/me')
  },

  async updateProfile(payload: UserProfileUpdatePayload): Promise<UserProfile> {
    return http.patch<any, UserProfile>('/auth/profile', payload)
  },

  async getDevToken(role: UserRole, phone?: string): Promise<AuthSession> {
    const data = await http.post<any, any>('/auth/dev-token', { role, phone })
    return {
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      user: data.user,
    }
  },
}
