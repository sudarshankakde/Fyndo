import { apiClient } from './apiClient'
import { ResponseEnvelope } from '@/types/api'

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

export interface StaffCreateData {
  staff_name: string
  phone: string
  pin: string
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

export const merchantService = {
  async onboardStore(data: MerchantOnboardData) {
    const res = await apiClient.post<ResponseEnvelope<{ id: string }>>('/merchants/onboard', data)
    return res.data.data
  },

  async configureStaff(data: StaffCreateData) {
    const res = await apiClient.post<ResponseEnvelope<{ staff_id: string }>>('/merchants/staff', data)
    return res.data.data
  },

  async getUploadSignature(folder: 'reels' | 'kyc', resourceType: 'video' | 'image' = 'video'): Promise<CloudinarySignResponse> {
    const res = await apiClient.post<ResponseEnvelope<CloudinarySignResponse>>('/media/sign-upload', {
      folder,
      resource_type: resourceType,
    })
    return res.data.data
  },

  async uploadMedia(file: File, folder: string = 'reels'): Promise<string> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('folder', folder)
    const res = await apiClient.post<ResponseEnvelope<{ url: string }>>('/media/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return res.data.data.url
  },

  async createReel(data: ReelCreatePayload) {
    const res = await apiClient.post<ResponseEnvelope<{ reel_id: string; status: string }>>('/reels', data)
    return res.data.data
  },
}
