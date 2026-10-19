import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, RefreshCw, AlertCircle, Compass } from 'lucide-react'
import { feedService } from '@/services/feedService'
import { DealDetailsModal } from '@/components/feed/DealDetailsModal'
import { Button } from '@/components/ui/Button'
import { ReelItem } from '@/types/reel'

export const ReelDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [isModalOpen, setIsModalOpen] = useState(true)

  const {
    data: reel,
    isLoading,
    isError,
  } = useQuery<ReelItem>({
    queryKey: ['reel-detail', id],
    queryFn: () => (id ? feedService.getReelById(id) : Promise.reject('No ID')),
    enabled: !!id,
    retry: 1,
  })

  useEffect(() => {
    if (reel) {
      setIsModalOpen(true)
    }
  }, [reel])

  if (isLoading) {
    return (
      <div className="py-24 text-center space-y-3 font-sans">
        <RefreshCw className="w-8 h-8 text-primary animate-spin mx-auto" />
        <p className="text-sm text-stone-500 font-medium">Loading offer details...</p>
      </div>
    )
  }

  if (isError || !reel) {
    return (
      <div className="max-w-md mx-auto my-16 bg-white p-8 rounded-3xl border border-stone-200 text-center space-y-4 font-sans shadow-card">
        <div className="w-14 h-14 rounded-2xl bg-amber-50 text-amber-600 flex items-center justify-center mx-auto">
          <AlertCircle className="w-7 h-7" />
        </div>
        <h2 className="text-xl font-black text-stone-900">Offer No Longer Available</h2>
        <p className="text-xs text-stone-500 leading-relaxed">
          This promotion may have expired or reached its maximum redemption cap. Explore more verified deals around you!
        </p>
        <div className="pt-2">
          <Button onClick={() => navigate('/')} variant="primary" size="md" className="gap-2">
            <Compass className="w-4 h-4" />
            <span>Discover Nearby Deals</span>
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="py-8 font-sans">
      <div className="flex items-center gap-2 mb-6">
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-1.5 text-xs font-bold text-stone-600 hover:text-stone-900"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Browse all deals</span>
        </button>
      </div>

      <DealDetailsModal
        reel={reel}
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false)
          navigate('/')
        }}
      />
    </div>
  )
}
