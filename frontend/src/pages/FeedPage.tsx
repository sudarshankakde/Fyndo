import React, { useState } from 'react'
import {
  RefreshCw,
  AlertCircle,
  Compass,
  Sparkles,
  MapPin,
  Tag,
  ShieldCheck,
  ChevronRight,
  TrendingUp,
} from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { feedService } from '@/services/feedService'
import { ReelCard } from '@/components/feed/ReelCard'
import { DealDetailsModal } from '@/components/feed/DealDetailsModal'
import { Button } from '@/components/ui/Button'
import { useAppDispatch, useAppSelector } from '@/store'
import { setRadiusKm, setSelectedSector } from '@/store/slices/uiSlice'
import { RADIUS_OPTIONS, SECTOR_DISPLAY_NAMES } from '@/config/constants'
import { ReelItem } from '@/types/reel'

export const FeedPage: React.FC = () => {
  const dispatch = useAppDispatch()
  const { location, radiusKm, selectedSector } = useAppSelector((state) => state.ui)
  const [selectedReel, setSelectedReel] = useState<ReelItem | null>(null)

  const {
    data: reels = [],
    isLoading,
    refetch,
    error,
  } = useQuery<ReelItem[]>({
    queryKey: ['reels', 'feed', location.lat, location.lon, radiusKm, selectedSector],
    queryFn: () =>
      feedService.getProximityFeed({
        lat: location.lat,
        lon: location.lon,
        radius_km: radiusKm,
        sector: selectedSector || undefined,
        limit: 20,
      }),
  })

  return (
    <div className="space-y-8 font-sans text-stone-900 pb-16">
      {/* Promotional Desktop Hero Banner (Amazon / Flipkart Style) */}
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-stone-900 via-stone-800 to-stone-900 text-white p-6 sm:p-10 shadow-xl border border-stone-800">
        <div className="relative z-10 max-w-2xl space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/20 text-rose-300 border border-primary/30 text-xs font-bold uppercase tracking-wider">
            <Sparkles className="w-3.5 h-3.5 text-primary" />
            <span>Hyperlocal Short Video Deals • {location.city || 'Nagpur'}</span>
          </div>

          <h1 className="text-2xl sm:text-4xl font-extrabold tracking-tight font-display leading-tight">
            Discover In-Store Deals. <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-rose-400 via-coral to-amber-300">
              Watch 30s Reels & Save Big.
            </span>
          </h1>

          <p className="text-xs sm:text-sm text-stone-300 leading-relaxed max-w-lg">
            Direct from verified local merchants in {location.city}. Claim instant digital vouchers and redeem at the counter with rotating 60s dynamic security codes.
          </p>

          {/* Quick Value Metrics */}
          <div className="grid grid-cols-3 gap-3 pt-2 max-w-md border-t border-stone-800/80">
            <div>
              <p className="text-lg sm:text-xl font-extrabold text-white font-mono">100%</p>
              <p className="text-[11px] text-stone-400">Verified Shops</p>
            </div>
            <div>
              <p className="text-lg sm:text-xl font-extrabold text-amber-400 font-mono">Up to 50%</p>
              <p className="text-[11px] text-stone-400">Instant Savings</p>
            </div>
            <div>
              <p className="text-lg sm:text-xl font-extrabold text-emerald-400 font-mono">60s</p>
              <p className="text-[11px] text-stone-400">Secure Dynamic QR</p>
            </div>
          </div>
        </div>

        {/* Ambient Decorative Glow */}
        <div className="absolute right-0 top-0 bottom-0 w-1/3 bg-radial from-primary/30 to-transparent pointer-events-none blur-3xl opacity-60" />
      </section>

      {/* Discovery Filters Bar */}
      <section className="bg-white rounded-2xl border border-stone-200 p-4 shadow-2xs space-y-3">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          {/* Left: Radius Pills */}
          <div className="flex items-center gap-2 overflow-x-auto w-full md:w-auto pb-1 md:pb-0 no-scrollbar">
            <span className="text-xs font-bold text-stone-500 uppercase tracking-wider shrink-0 mr-1 flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5 text-primary" />
              <span>Search Distance:</span>
            </span>
            {RADIUS_OPTIONS.map((r) => (
              <button
                key={r}
                onClick={() => dispatch(setRadiusKm(r))}
                className={`px-3 py-1.5 rounded-full text-xs font-bold transition-all shrink-0 border ${
                  radiusKm === r
                    ? 'bg-stone-900 text-white border-stone-900 shadow-xs'
                    : 'bg-stone-50 text-stone-600 border-stone-200 hover:bg-stone-100'
                }`}
              >
                {r} km
              </button>
            ))}
          </div>

          {/* Right: Active Location & Refresh Status */}
          <div className="flex items-center gap-3 w-full md:w-auto justify-between md:justify-end text-xs">
            <span className="text-stone-500 font-medium">
              Showing verified stores around <strong className="text-stone-900">{location.city}</strong>
            </span>
            <Button variant="outline" size="sm" onClick={() => refetch()} className="text-xs shrink-0">
              <RefreshCw className="w-3.5 h-3.5 mr-1" />
              Refresh Deals
            </Button>
          </div>
        </div>

        {/* Sector Category Chips */}
        <div className="flex items-center gap-2 overflow-x-auto pt-2 border-t border-stone-100 no-scrollbar">
          <button
            onClick={() => dispatch(setSelectedSector(null))}
            className={`px-3 py-1 rounded-full text-xs font-bold transition-all shrink-0 border ${
              !selectedSector
                ? 'bg-primary text-white border-primary shadow-xs'
                : 'bg-stone-50 text-stone-600 border-stone-200 hover:bg-stone-100'
            }`}
          >
            All Categories
          </button>
          {[
            { value: 'FOOD', label: '🍔 Food & Dining' },
            { value: 'FASHION', label: '👗 Fashion' },
            { value: 'FOOTWEAR', label: '👟 Footwear' },
            { value: 'ELECTRONICS', label: '📱 Electronics' },
            { value: 'REAL_ESTATE', label: '🏢 Real Estate' },
          ].map((sec) => (
            <button
              key={sec.value}
              onClick={() => dispatch(setSelectedSector(sec.value))}
              className={`px-3 py-1 rounded-full text-xs font-bold transition-all shrink-0 border ${
                selectedSector === sec.value
                  ? 'bg-primary text-white border-primary shadow-xs'
                  : 'bg-stone-50 text-stone-600 border-stone-200 hover:bg-stone-100'
              }`}
            >
              {sec.label}
            </button>
          ))}
        </div>
      </section>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-2xl bg-red-50 border border-red-200 text-red-700 text-xs font-medium flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
            <span>Unable to load deals near your location.</span>
          </div>
          <Button variant="outline" size="sm" onClick={() => refetch()} className="text-xs">
            Retry
          </Button>
        </div>
      )}

      {/* Loading Skeleton Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {[...Array(8)].map((_, i) => (
            <div
              key={i}
              className="aspect-[9/16] rounded-3xl bg-stone-100 animate-pulse border border-stone-200/80 p-4 flex flex-col justify-between"
            >
              <div className="flex justify-between">
                <div className="w-16 h-5 rounded-full bg-stone-200" />
                <div className="w-12 h-5 rounded-full bg-stone-200" />
              </div>
              <div className="space-y-2">
                <div className="w-3/4 h-4 rounded bg-stone-200" />
                <div className="w-1/2 h-3 rounded bg-stone-200" />
                <div className="w-full h-10 rounded-xl bg-stone-200 mt-2" />
              </div>
            </div>
          ))}
        </div>
      ) : reels.length > 0 ? (
        <div className="space-y-8">
          {/* Main 4-Column Responsive Deals Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {reels.map((reel) => (
              <ReelCard
                key={reel.id}
                reel={reel}
                onSelect={(r) => setSelectedReel(r)}
              />
            ))}
          </div>

          {/* End-of-feed Banner */}
          <div className="bg-white rounded-3xl border border-stone-200 p-8 text-center shadow-card space-y-3 max-w-xl mx-auto">
            <h4 className="text-base font-extrabold text-stone-900">
              You have explored all deals within {radiusKm} km in {location.city}
            </h4>
            <p className="text-xs text-stone-500 leading-relaxed">
              Expand your search radius to discover exclusive food, fashion, and electronic deals across neighboring localities.
            </p>
            <div className="flex justify-center gap-2 pt-2">
              {radiusKm < 10 && (
                <Button size="sm" variant="primary" onClick={() => dispatch(setRadiusKm(10))}>
                  Expand to 10 km Search
                </Button>
              )}
              <Button size="sm" variant="outline" onClick={() => refetch()}>
                Refresh Live Feed
              </Button>
            </div>
          </div>
        </div>
      ) : (
        /* Empty State */
        <div className="bg-white rounded-3xl border border-stone-200 p-12 text-center shadow-card space-y-4 max-w-md mx-auto my-12">
          <div className="w-16 h-16 rounded-full bg-amber-50 text-amber-600 flex items-center justify-center mx-auto">
            <Compass className="w-8 h-8" />
          </div>
          <h3 className="text-lg font-extrabold text-stone-900">
            No live store deals within {radiusKm} km
          </h3>
          <p className="text-xs text-stone-500 leading-relaxed">
            We are currently rolling out store partnerships in Nagpur & Mumbai. Try expanding your radius to 5 km or 10 km to see verified deals.
          </p>
          <div className="flex justify-center gap-2 pt-2">
            {radiusKm < 10 && (
              <Button
                variant="primary"
                size="sm"
                onClick={() => dispatch(setRadiusKm(radiusKm === 2 ? 5 : 10))}
              >
                Expand Radius to {radiusKm === 2 ? '5 km' : '10 km'}
              </Button>
            )}
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              Refresh
            </Button>
          </div>
        </div>
      )}

      {/* Expanded Deal & Store Details Modal */}
      <DealDetailsModal
        reel={selectedReel}
        isOpen={!!selectedReel}
        onClose={() => setSelectedReel(null)}
      />
    </div>
  )
}
