import { http } from './http'

export interface AdminStatsResponse {
  total_users: number
  total_merchants: number
  total_reels: number
  active_reels: number
  total_redemptions: number
  pending_moderation_count: number
}

export interface AdminMerchantDetail {
  id: string
  business_name: string
  sector: string
  city: string
  address_text: string
  kyc_status: string
  kyc_rejection_reason?: string | null
  kyc_doc_url?: string | null
  owner_phone?: string
  staff_count: number
  reels_count: number
  created_at: string
}

export interface AdminKycMerchantItem {
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

export const adminService = {
  async getStats(): Promise<AdminStatsResponse> {
    return http.get<any, AdminStatsResponse>('/admin/stats')
  },

  async listMerchants(): Promise<AdminMerchantDetail[]> {
    return http.get<any, AdminMerchantDetail[]>('/admin/merchants')
  },

  async listKycQueue(statusFilter?: string): Promise<AdminKycMerchantItem[]> {
    return http.get<any, AdminKycMerchantItem[]>('/admin/moderation/merchants', {
      params: statusFilter ? { status: statusFilter } : undefined,
    })
  },

  async decideKyc(
    merchantId: string,
    decision: 'APPROVE' | 'REJECT',
    rejectionReason?: string
  ): Promise<any> {
    return http.post<any, any>(`/admin/moderation/merchants/${merchantId}/decision`, {
      decision,
      rejection_reason: rejectionReason,
    })
  },

  async getPendingReels(): Promise<AdminPendingReel[]> {
    return http.get<any, AdminPendingReel[]>('/admin/moderation/reels')
  },

  async decideReel(
    reelId: string,
    decision: 'APPROVE' | 'REJECT',
    rejectionReason?: string
  ): Promise<{ reel_id: string; status: string }> {
    return http.post<any, { reel_id: string; status: string }>(
      `/admin/moderation/reels/${reelId}/decision`,
      {
        decision,
        rejection_reason: rejectionReason,
      }
    )
  },
}
