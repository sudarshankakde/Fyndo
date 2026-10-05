import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { couponService } from '@/services/couponService'

export function useDynamicQr(userCouponId: string | null, isOpen: boolean) {
  const [secondsRemaining, setSecondsRemaining] = useState<number>(60)

  const query = useQuery({
    queryKey: ['dynamic-qr', userCouponId],
    queryFn: () => (userCouponId ? couponService.getDynamicQr(userCouponId) : null),
    enabled: !!userCouponId && isOpen,
    refetchInterval: (query) => {
      // Auto-refetch when seconds remaining hits 0
      const remaining = query.state.data?.time_step_remaining_seconds ?? 60
      return Math.max(remaining, 1) * 1000
    },
    refetchOnWindowFocus: true,
  })

  // Local ticker for smooth countdown ring animation
  useEffect(() => {
    if (!query.data?.time_step_remaining_seconds) return
    setSecondsRemaining(query.data.time_step_remaining_seconds)

    const timer = setInterval(() => {
      setSecondsRemaining((prev) => {
        if (prev <= 1) {
          query.refetch()
          return 60
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(timer)
  }, [query.data, query.refetch])

  return {
    qrData: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    secondsRemaining,
    refetch: query.refetch,
  }
}
