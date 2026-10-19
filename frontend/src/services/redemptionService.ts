import { http } from './http'
import { RedemptionVerifyResult } from '@/types/coupon'

export interface VerifyRedemptionRequest {
  qr_payload: string
  bill_amount: number
  cashier_lat?: number
  cashier_lon?: number
}

export interface VerifyPinRedemptionRequest {
  user_coupon_id: string
  backup_pin: string
  bill_amount: number
  cashier_lat?: number
  cashier_lon?: number
}

export interface MerchantRedemptionRecord {
  redemption_id: string
  coupon_id: string
  coupon_title: string
  shopper_name: string
  bill_amount: number
  discount_applied: number
  staff_id: string | null
  created_at: string
}

export interface ShopperRedemptionRecord {
  redemption_id: string
  coupon_id: string
  coupon_title: string
  merchant_id: string
  merchant_name: string
  staff_name?: string | null
  discount_type: string
  bill_amount: number
  discount_applied: number
  created_at: string
}

export interface MerchantAnalyticsSummary {
  merchant_id: string
  redemption_count: number
  total_bill_amount: number
  total_discount_applied: number
  reels_count: number
  from_date?: string | null
  to_date?: string | null
}

export const redemptionService = {
  async verifyAndRedeem(data: VerifyRedemptionRequest): Promise<RedemptionVerifyResult> {
    return http.post<any, RedemptionVerifyResult>('/redemptions/verify', data)
  },

  async verifyPin(data: VerifyPinRedemptionRequest): Promise<RedemptionVerifyResult> {
    return http.post<any, RedemptionVerifyResult>('/redemptions/verify-pin', data)
  },

  async getMerchantRedemptions(params?: {
    from_date?: string
    to_date?: string
  }): Promise<MerchantRedemptionRecord[]> {
    return http.get<any, MerchantRedemptionRecord[]>('/merchants/redemptions', { params })
  },

  async getMerchantAnalytics(params?: {
    from_date?: string
    to_date?: string
  }): Promise<MerchantAnalyticsSummary> {
    return http.get<any, MerchantAnalyticsSummary>('/merchants/analytics', { params })
  },

  async getShopperHistory(): Promise<ShopperRedemptionRecord[]> {
    return http.get<any, ShopperRedemptionRecord[]>('/redemptions/my-history')
  },
}
