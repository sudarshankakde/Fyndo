import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { couponService } from '@/services/couponService'

export function useDynamicQr(userCouponId: string | null, isOpen: boolean) {
  const [secondsRemaining, setSecondsRemaining] = useState<number>(60)
  const [isVisible, setIsVisible] = useState<boolean>(
    typeof document !== 'undefined' ? document.visibilityState === 'visible' : true
  )

  useEffect(() => {
    const handleVisibility = () => {
      setIsVisible(document.visibilityState === 'visible')
    }
    document.addEventListener('visibilitychange', handleVisibility)
    return () => document.removeEventListener('visibilitychange', handleVisibility)
  }, [])

  const query = useQuery({
    queryKey: ['dynamic-qr', userCouponId],
    queryFn: () => (userCouponId ? couponService.getDynamicQr(userCouponId) : null),
    enabled: !!userCouponId && isOpen && isVisible,
    refetchInterval: (q) => {
      if (!isVisible) return false
      const remaining = q.state.data?.time_step_remaining_seconds ?? 60
      return Math.max(remaining, 1) * 1000
    },
    refetchOnWindowFocus: true,
  })

  // Local ticker for smooth countdown ring animation
  useEffect(() => {
    if (!isVisible || !query.data?.time_step_remaining_seconds) return
    setSecondsRemaining(query.data.time_step_remaining_seconds)

    const timer = setInterval(() => {
      if (document.visibilityState === 'hidden') return
      setSecondsRemaining((prev) => {
        if (prev <= 1) {
          query.refetch()
          return 60
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(timer)
  }, [query.data, query.refetch, isVisible])

  return {
    qrData: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    secondsRemaining,
    refetch: query.refetch,
  }
}
