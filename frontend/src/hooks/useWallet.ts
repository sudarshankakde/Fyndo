import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { couponService } from '@/services/couponService'
import { useAppSelector } from '@/store'

export function useWallet() {
  const queryClient = useQueryClient()
  const isAuthenticated = useAppSelector((state) => state.auth.isAuthenticated)

  const walletQuery = useQuery({
    queryKey: ['wallet'],
    queryFn: () => couponService.getUserWallet(),
    enabled: isAuthenticated,
    staleTime: 1000 * 15,
  })

  const claimMutation = useMutation({
    mutationFn: (couponTemplateId: string) => couponService.claimCoupon(couponTemplateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wallet'] })
    },
  })

  return {
    coupons: walletQuery.data || [],
    isLoading: walletQuery.isLoading,
    isError: walletQuery.isError,
    refetchWallet: walletQuery.refetch,
    claimCoupon: claimMutation.mutateAsync,
    isClaiming: claimMutation.isPending,
  }
}
