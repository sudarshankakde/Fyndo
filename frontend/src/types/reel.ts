import { SectorType } from './api'

export interface MerchantFeedSummary {
  id: string
  business_name: string
  sector: SectorType
  address: string
  distance_meters: number
}

export interface CouponFeedSummary {
  id: string
  title: string
  discount_type: 'PERCENTAGE' | 'FLAT_AMOUNT' | 'BOGO'
  discount_value: number
  min_order_amount: number
  validity_days: number
}

export interface ReelItem {
  id: string
  title: string
  video_url: string
  thumbnail_url: string
  duration_seconds: number
  views_count: number
  merchant: MerchantFeedSummary
  coupon?: CouponFeedSummary | null
}

export interface FeedQueryParams {
  lat: number
  lon: number
  radius_km: number
  sector?: string
  limit?: number
}
