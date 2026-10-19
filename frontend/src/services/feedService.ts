import { http } from './http'
import { FeedQueryParams, ReelItem } from '@/types/reel'

export interface ReelComment {
  id: string
  parent_comment_id?: string | null
  user_name: string
  user_initial: string
  profile_image_url?: string | null
  text: string
  created_at: string
  is_store_reply: boolean
}

export interface PublicStorefrontData {
  id: string
  business_name: string
  sector: string
  address_text: string
  city: string
  latitude: number
  longitude: number
}

export const feedService = {
  async getProximityFeed(params: FeedQueryParams): Promise<ReelItem[]> {
    return http.get<any, ReelItem[]>('/reels/feed', {
      params: {
        lat: params.lat,
        lon: params.lon,
        radius_km: params.radius_km,
        sector: params.sector || undefined,
        limit: params.limit || 20,
        cursor: (params as any).cursor || undefined,
      },
    })
  },

  async getReelById(reelId: string): Promise<ReelItem> {
    return http.get<any, ReelItem>(`/reels/${reelId}`)
  },

  async recordView(reelId: string, viewerKey?: string): Promise<{ views_count: number; counted: boolean }> {
    try {
      return await http.post<any, any>(`/reels/${reelId}/view`, null, {
        params: viewerKey ? { viewer_key: viewerKey } : undefined,
      })
    } catch {
      return { views_count: 0, counted: false }
    }
  },

  async toggleLike(reelId: string): Promise<{ liked: boolean; likes_count: number }> {
    return http.post<any, { liked: boolean; likes_count: number }>(`/reels/${reelId}/like`)
  },

  async getComments(reelId: string): Promise<ReelComment[]> {
    return http.get<any, ReelComment[]>(`/reels/${reelId}/comments`)
  },

  async postComment(
    reelId: string,
    text: string,
    parentCommentId?: string | null
  ): Promise<ReelComment> {
    return http.post<any, ReelComment>(`/reels/${reelId}/comments`, {
      text,
      parent_comment_id: parentCommentId || undefined,
    })
  },

  async getPublicStorefront(merchantId: string): Promise<PublicStorefrontData> {
    return http.get<any, PublicStorefrontData>(`/merchants/${merchantId}`)
  },
}
