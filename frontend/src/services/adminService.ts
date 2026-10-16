import { apiClient } from './apiClient'
import { ResponseEnvelope } from '@/types/api'

export interface AdminPendingReel {
  id: string
  title: string
  video_url: string
  thumbnail_url: string
  duration_seconds: number
  audio_type: string
  status: string
  merchant_id: string
  merchant_name: string
  sector: string
  city: string
  coupon_title?: string | null
  discount_type?: string | null
  discount_value?: number | null
  min_order_amount?: number | null
  validity_days?: number | null
}

export interface AdminStats {
  total_merchants: number
  total_users: number
  total_reels: number
  total_redemptions: number
  total_discount_applied: number
  pending_moderation_count: number
}

export interface AdminMerchantItem {
  id: string
  business_name: string
  sector: string
  address_text: string
  city: string
  latitude: number
  longitude: number
  owner_phone: string
  kyc_status: string
  staff_name?: string | null
  staff_phone?: string | null
  reels_count: number
  created_at: string
}

export interface AdminKycItem {
  id: string
  business_name: string
  sector: string
  city: string
  kyc_doc_url: string
  kyc_status: string
  kyc_rejection_reason?: string | null
  owner_phone: string
  submitted_at: string
}

export interface CreateMerchantPayload {
  owner_phone: string
  business_name: string
  sector: string
  address_text: string
  city: string
  latitude: number
  longitude: number
  gstin?: string
  staff_name?: string
  staff_pin?: string
}

export interface CreateReelPayload {
  merchant_id: string
  title: string
  video_url: string
  thumbnail_url: string
  duration_seconds: number
  coupon_title: string
  discount_type: string
  discount_value: number
  validity_days: number
  min_order_amount: number
}

export const adminService = {
  async getStats(): Promise<AdminStats> {
    const res = await apiClient.get<ResponseEnvelope<AdminStats>>('/admin/stats')
    return res.data.data
  },

  async getPendingReels(): Promise<AdminPendingReel[]> {
    const res = await apiClient.get<ResponseEnvelope<AdminPendingReel[]>>('/admin/moderation/reels')
    return res.data.data
  },

  async getAllReels(status?: string): Promise<AdminPendingReel[]> {
    const res = await apiClient.get<ResponseEnvelope<AdminPendingReel[]>>('/admin/reels', {
      params: { status },
    })
    return res.data.data
  },

  async decideReel(reelId: string, decision: 'APPROVE' | 'REJECT', rejectionReason?: string) {
    const res = await apiClient.post<ResponseEnvelope<{ reel_id: string; status: string }>>(
      `/admin/moderation/reels/${reelId}/decision`,
      {
        decision,
        rejection_reason: rejectionReason,
      }
    )
    return res.data.data
  },

  async createReel(payload: CreateReelPayload) {
    const res = await apiClient.post<ResponseEnvelope<{ reel_id: string }>>(
      '/admin/reels',
      payload
    )
    return res.data.data
  },

  async getMerchants(): Promise<AdminMerchantItem[]> {
    const res = await apiClient.get<ResponseEnvelope<AdminMerchantItem[]>>('/admin/merchants')
    return res.data.data
  },

  async getKycSubmissions(status?: 'PENDING' | 'APPROVED' | 'REJECTED'): Promise<AdminKycItem[]> {
    const res = await apiClient.get<ResponseEnvelope<AdminKycItem[]>>('/admin/moderation/merchants', {
      params: { status },
    })
    return res.data.data
  },

  async decideKyc(merchantId: string, decision: 'APPROVE' | 'REJECT', rejectionReason?: string) {
    const res = await apiClient.post<ResponseEnvelope<{ merchant_id: string; kyc_status: string }>>(
      `/admin/moderation/merchants/${merchantId}/decision`,
      { decision, rejection_reason: rejectionReason },
    )
    return res.data.data
  },

  async createMerchant(payload: CreateMerchantPayload): Promise<AdminMerchantItem> {
    const res = await apiClient.post<ResponseEnvelope<AdminMerchantItem>>(
      '/admin/merchants',
      payload
    )
    return res.data.data
  },

  async updateMerchant(merchantId: string, payload: Partial<CreateMerchantPayload>) {
    const res = await apiClient.put<ResponseEnvelope<{ merchant_id: string }>>(
      `/admin/merchants/${merchantId}`,
      payload
    )
    return res.data.data
  },

  async updateStaff(merchantId: string, payload: { staff_name: string; phone: string; pin: string }) {
    const res = await apiClient.put<ResponseEnvelope<{ staff_id: string; staff_name: string }>>(
      `/admin/merchants/${merchantId}/staff`,
      payload
    )
    return res.data.data
  },
}
