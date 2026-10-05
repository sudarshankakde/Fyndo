import { apiClient } from './apiClient'
import { ResponseEnvelope, SupportedLanguage } from '@/types/api'
import {
  AdminLoginPayload,
  AuthSession,
  RefreshTokenResponseData,
  StaffSession,
  UserProfile,
  UserProfileUpdatePayload,
  UserRole,
} from '@/types/auth'

interface OtpSendResult {
  phone: string
  expires_in_seconds: number
  test_otp?: string
}

interface OtpVerifyResponse {
  access_token: string
  refresh_token: string
  user: UserProfile
}

interface StaffLoginResponse {
  access_token: string
  refresh_token?: string
  staff_id: string
  staff_name: string
  merchant_id: string
  business_name: string
}

interface DevTokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  role: string
  user: UserProfile
}

export const authService = {
  async sendOtp(phone: string, channel: 'SMS' | 'WHATSAPP' = 'SMS'): Promise<OtpSendResult> {
    const res = await apiClient.post<ResponseEnvelope<OtpSendResult>>('/auth/otp/send', {
      phone,
      channel,
    })
    return res.data.data
  },

  async verifyOtp(
    phone: string,
    otp: string,
    preferredLanguage: SupportedLanguage = 'en'
  ): Promise<AuthSession> {
    const res = await apiClient.post<ResponseEnvelope<OtpVerifyResponse>>('/auth/otp/verify', {
      phone,
      otp,
      preferred_language: preferredLanguage,
    })
    const data = res.data.data
    return {
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      user: data.user,
    }
  },

  async staffLogin(storePhone: string, pin: string): Promise<StaffSession> {
    const res = await apiClient.post<ResponseEnvelope<StaffLoginResponse>>('/auth/staff-login', {
      store_phone: storePhone,
      pin,
    })
    const data = res.data.data
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
    const res = await apiClient.post<ResponseEnvelope<OtpVerifyResponse>>('/auth/admin-login', payload)
    const data = res.data.data
    return {
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      user: data.user,
    }
  },

  async refreshToken(refreshToken: string): Promise<RefreshTokenResponseData> {
    const res = await apiClient.post<ResponseEnvelope<RefreshTokenResponseData>>('/auth/refresh', {
      refresh_token: refreshToken,
    })
    return res.data.data
  },

  async logout(refreshToken?: string): Promise<void> {
    await apiClient.post('/auth/logout', { refresh_token: refreshToken })
  },

  async getMe(): Promise<UserProfile> {
    const res = await apiClient.get<ResponseEnvelope<UserProfile>>('/auth/me')
    return res.data.data
  },

  async updateProfile(payload: UserProfileUpdatePayload): Promise<UserProfile> {
    const res = await apiClient.patch<ResponseEnvelope<UserProfile>>('/auth/profile', payload)
    return res.data.data
  },

  async getDevToken(role: UserRole): Promise<AuthSession> {
    const res = await apiClient.post<ResponseEnvelope<DevTokenResponse>>('/auth/dev-token', { role })
    const data = res.data.data
    return {
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      user: data.user,
    }
  },
}
