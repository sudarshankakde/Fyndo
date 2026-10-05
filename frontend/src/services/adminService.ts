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

export const adminService = {
  async getPendingReels(): Promise<AdminPendingReel[]> {
    const res = await apiClient.get<ResponseEnvelope<AdminPendingReel[]>>('/admin/moderation/reels')
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
}
