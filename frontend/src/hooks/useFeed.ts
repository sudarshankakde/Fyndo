import { useQuery } from '@tanstack/react-query'
import { feedService } from '@/services/feedService'
import { useAppSelector } from '@/store'

export function useFeed() {
  const { location, radiusKm, selectedSector } = useAppSelector((state) => state.ui)

  const query = useQuery({
    queryKey: ['feed', location.lat, location.lon, radiusKm, selectedSector],
    queryFn: () =>
      feedService.getProximityFeed({
        lat: location.lat,
        lon: location.lon,
        radius_km: radiusKm,
        sector: selectedSector || undefined,
      }),
    staleTime: 1000 * 30, // 30 seconds
    refetchOnWindowFocus: false,
  })

  return {
    reels: query.data || [],
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  }
}
