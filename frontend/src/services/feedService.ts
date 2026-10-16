import { apiClient } from './apiClient'
import { ResponseEnvelope } from '@/types/api'
import { FeedQueryParams, ReelItem } from '@/types/reel'

export const feedService = {
  async getProximityFeed(params: FeedQueryParams & { cursor?: string }): Promise<ReelItem[]> {
    const res = await apiClient.get<ResponseEnvelope<ReelItem[]>>('/reels/feed', {
      params: {
        lat: params.lat,
        lon: params.lon,
        radius_km: params.radius_km,
        sector: params.sector || undefined,
        limit: params.limit || 15,
        cursor: params.cursor,
      },
    })
    return res.data.data
  },
}
