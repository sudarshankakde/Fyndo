import React, { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  ArrowLeft,
  Share2,
  Phone,
  Navigation,
  ShieldCheck,
  MapPin,
  RefreshCw,
  Compass,
  AlertCircle,
  Tag,
} from 'lucide-react'
import { feedService, PublicStorefrontData } from '@/services/feedService'
import { ReelCard } from '@/components/feed/ReelCard'
import { DealDetailsModal } from '@/components/feed/DealDetailsModal'
import { Button } from '@/components/ui/Button'
import { ReelItem } from '@/types/reel'

export const StorefrontPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [selectedReel, setSelectedReel] = useState<ReelItem | null>(null)

  const {
    data: store,
    isLoading: isStoreLoading,
    error: storeError,
  } = useQuery<PublicStorefrontData>({
    queryKey: ['storefront', id],
    queryFn: () => (id ? feedService.getPublicStorefront(id) : Promise.reject('No ID')),
    enabled: !!id,
  })

  // Also fetch proximity feed to show deals from this merchant or nearby
  const { data: allReels = [] } = useQuery<ReelItem[]>({
    queryKey: ['reels', 'store', id],
    queryFn: () =>
      store
        ? feedService.getProximityFeed({
            lat: store.latitude,
            lon: store.longitude,
            radius_km: 10,
          })
        : Promise.resolve([]),
    enabled: !!store,
  })

  const storeReels = allReels.filter((r) => r.merchant.id === id)

  if (isStoreLoading) {
    return (
      <div className="py-24 text-center space-y-3 font-sans">
        <RefreshCw className="w-8 h-8 text-primary animate-spin mx-auto" />
        <p className="text-sm text-stone-500 font-medium">Loading store showcase...</p>
      </div>
    )
  }

  if (storeError || !store) {
    return (
      <div className="max-w-md mx-auto my-16 bg-white p-8 rounded-3xl border border-stone-200 text-center space-y-4 font-sans">
        <AlertCircle className="w-10 h-10 text-stone-400 mx-auto" />
        <h2 className="text-lg font-black text-stone-900">Store Not Found</h2>
        <p className="text-xs text-stone-500">
          This store is either inactive or currently undergoing merchant verification.
        </p>
        <Button onClick={() => navigate('/')} variant="primary" size="sm">
          Discover Other Stores
        </Button>
      </div>
    )
  }

  const handleDirections = () => {
    const query = encodeURIComponent(`${store.business_name}, ${store.address_text}, ${store.city}`)
    window.open(`https://www.google.com/maps/search/?api=1&query=${query}`, '_blank')
  }

  const handleShare = () => {
    if (navigator.share) {
      navigator.share({
        title: store.business_name,
        text: `Check out exclusive deals at ${store.business_name} on Fyndo!`,
        url: window.location.href,
      }).catch(() => {})
    } else {
      navigator.clipboard.writeText(window.location.href)
      alert('Store link copied to clipboard!')
    }
  }

  return (
    <div className="space-y-6 font-sans text-stone-900 pb-16">
      {/* Top Header Bar */}
      <div className="flex items-center justify-between pb-3 border-b border-stone-200/60">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-1.5 text-xs font-bold text-stone-600 hover:text-stone-900"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back</span>
        </button>
        <button
          onClick={handleShare}
          className="p-2 rounded-full border border-stone-200 hover:bg-stone-50 text-stone-600 transition-colors"
          aria-label="Share Store"
        >
          <Share2 className="w-4 h-4" />
        </button>
      </div>

      {/* Cinematic Hero Card (Stitch Screen 2 Inspiration) */}
      <div className="relative rounded-3xl overflow-hidden bg-stone-900 text-white p-6 sm:p-10 shadow-lg border border-stone-800">
        <div className="relative z-10 space-y-4 max-w-xl">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary/20 text-rose-300 border border-primary/30 text-xs font-bold uppercase tracking-wider">
            <Tag className="w-3.5 h-3.5 text-primary" />
            <span>Fyndo Verified Merchant</span>
          </div>

          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl sm:text-4xl font-extrabold tracking-tight font-display">
                {store.business_name}
              </h1>
              <ShieldCheck className="w-6 h-6 text-emerald-400 shrink-0" />
            </div>
            <p className="text-xs sm:text-sm text-stone-300 mt-1 flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5 text-primary shrink-0" />
              <span>{store.address_text}, {store.city}</span>
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 pt-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-400/20 text-amber-300 border border-amber-400/30 uppercase">
              {store.sector}
            </span>
            <span className="text-xs text-stone-300">• Open for In-Store Savings</span>
          </div>
        </div>

        {/* Action Pills Grid */}
        <div className="relative z-10 grid grid-cols-2 sm:grid-cols-3 gap-3 pt-6 max-w-md">
          <Button
            variant="outline"
            size="sm"
            onClick={handleDirections}
            className="bg-white/10 hover:bg-white/20 text-white border-white/20 text-xs font-bold gap-2"
          >
            <Navigation className="w-4 h-4 text-primary" />
            <span>Directions</span>
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleShare}
            className="bg-white/10 hover:bg-white/20 text-white border-white/20 text-xs font-bold gap-2"
          >
            <Share2 className="w-4 h-4 text-emerald-400" />
            <span>Share Store</span>
          </Button>
        </div>
      </div>

      {/* Store Deals & Showcases */}
      <div className="space-y-4 pt-2">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-black text-stone-900 tracking-tight">
            Active Store Offers ({storeReels.length})
          </h2>
          <span className="text-xs font-bold text-primary">In-Store Redemptions</span>
        </div>

        {storeReels.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {storeReels.map((reel) => (
              <ReelCard key={reel.id} reel={reel} onSelect={(r) => setSelectedReel(r)} />
            ))}
          </div>
        ) : (
          <div className="bg-white rounded-3xl border border-stone-200/80 p-10 text-center space-y-3 shadow-xs">
            <Compass className="w-8 h-8 text-stone-400 mx-auto" />
            <h3 className="text-sm font-black text-stone-800">No active promotional reels today</h3>
            <p className="text-xs text-stone-500 max-w-sm mx-auto">
              This store is registered on Fyndo. Follow this store or check back soon for seasonal discounts!
            </p>
          </div>
        )}
      </div>

      <DealDetailsModal
        reel={selectedReel}
        isOpen={!!selectedReel}
        onClose={() => setSelectedReel(null)}
      />
    </div>
  )
}
