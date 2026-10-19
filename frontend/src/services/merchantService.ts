import { http } from './http'

export interface MerchantOnboardData {
  business_name: string
  sector: string
  address_text: string
  city: string
  latitude: number
  longitude: number
  gstin?: string
  kyc_doc_url: string
}

export interface MerchantProfileData {
  id: string
  user_id: string
  business_name: string
  sector: string
  address_text: string
  city: string
  latitude: number
  longitude: number
  gstin?: string | null
  kyc_doc_url?: string | null
  kyc_status: 'PENDING' | 'APPROVED' | 'REJECTED'
  kyc_rejection_reason?: string | null
}

export interface StaffCreateData {
  staff_name: string
  phone: string
  pin: string
}

export interface StaffResponseData {
  id: string
  merchant_id: string
  staff_name: string
  phone: string
  is_active: boolean
}

export interface CloudinarySignResponse {
  cloud_name: string
  api_key: string
  timestamp: number
  signature: string
  folder: string
  upload_url: string
}

export interface ReelCreatePayload {
  title: string
  video_url: string
  thumbnail_url: string
  duration_seconds: number
  audio_type: 'CAMERA_MIC' | 'VOICEOVER'
  coupon: {
    title: string
    discount_type: 'PERCENTAGE' | 'FLAT_AMOUNT' | 'BOGO'
    discount_value: number
    min_order_amount: number
    validity_days: number
    terms?: string
  }
}

export interface MerchantReelItem {
  id: string
  title: string
  video_url: string
  thumbnail_url: string
  duration_seconds: number
  status: 'PENDING_MODERATION' | 'APPROVED' | 'REJECTED'
  rejection_reason?: string | null
  views_count: number
  allow_comments: boolean
  created_at: string
  updated_at: string
  deleted_at?: string | null
}

export const merchantService = {
  async onboardStore(data: MerchantOnboardData): Promise<MerchantProfileData> {
    return http.post<any, MerchantProfileData>('/merchants/onboard', data)
  },

  async getProfile(): Promise<MerchantProfileData> {
    return http.get<any, MerchantProfileData>('/merchants/profile')
  },

  async resubmitKyc(data: { kyc_doc_url: string; gstin?: string }): Promise<MerchantProfileData> {
    return http.patch<any, MerchantProfileData>('/merchants/kyc', data)
  },

  async configureStaff(data: StaffCreateData): Promise<StaffResponseData> {
    return http.post<any, StaffResponseData>('/merchants/staff', data)
  },

  async listStaff(): Promise<StaffResponseData[]> {
    return http.get<any, StaffResponseData[]>('/merchants/staff')
  },

  async updateStaff(
    staffId: string,
    data: { staff_name?: string; pin?: string; is_active?: boolean }
  ): Promise<StaffResponseData> {
    return http.patch<any, StaffResponseData>(`/merchants/staff/${staffId}`, data)
  },

  async getUploadSignature(
    folder: 'reels' | 'kyc',
    resourceType: 'video' | 'image' = 'video'
  ): Promise<CloudinarySignResponse> {
    return http.post<any, CloudinarySignResponse>('/media/sign-upload', {
      folder,
      resource_type: resourceType,
    })
  },

  async createReel(data: ReelCreatePayload): Promise<{ reel_id: string; status: string }> {
    return http.post<any, { reel_id: string; status: string }>('/reels', data)
  },

  async listMyReels(): Promise<MerchantReelItem[]> {
    return http.get<any, MerchantReelItem[]>('/reels/mine')
  },

  async updateReel(reelId: string, data: { title?: string; allow_comments?: boolean }): Promise<MerchantReelItem> {
    return http.patch<any, MerchantReelItem>(`/reels/${reelId}`, data)
  },

  async deleteReel(reelId: string): Promise<{ reel_id: string; deleted: boolean }> {
    return http.delete<any, { reel_id: string; deleted: boolean }>(`/reels/${reelId}`)
  },
}
