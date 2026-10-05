import React from 'react'
import { Sparkles, MapPin, RefreshCw } from 'lucide-react'
import { useFeed } from '@/hooks/useFeed'
import { ReelCard } from '@/components/feed/ReelCard'
import { RadiusFilter } from '@/components/feed/RadiusFilter'
import { SectorFilter } from '@/components/feed/SectorFilter'
import { Button } from '@/components/ui/Button'
import { useTranslation } from '@/hooks/useTranslation'
import { ReelItem } from '@/types/reel'

// High-quality hyper-local seed deals for Nagpur Beta pilot
const FALLBACK_NAGPUR_REELS: ReelItem[] = [
  {
    id: 'f101-sample-nagpur',
    title: 'Crispy Nagpur Samosa & Jalebi with special Tarri',
    video_url: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',
    thumbnail_url: 'https://images.unsplash.com/photo-1601050690597-df0568f70950?w=600&auto=format&fit=crop',
    duration_seconds: 28,
    views_count: 1420,
    merchant: {
      id: 'm101-sitabuldi',
      business_name: 'Sitabuldi Famous Sweets & Farsan',
      sector: 'FOOD',
      address: 'Main Market, Sitabuldi, Nagpur',
      distance_meters: 450,
    },
    coupon: {
      id: 'c101-sweets',
      title: 'Flat 30% Off on Evening Sweets & Snacks',
      discount_type: 'PERCENTAGE',
      discount_value: 30,
      min_order_amount: 150,
      validity_days: 3,
    },
  },
  {
    id: 'f102-sample-nagpur',
    title: 'Exclusive Paithani & Festive Silk Sarees Clearance',
    video_url: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4',
    thumbnail_url: 'https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=600&auto=format&fit=crop',
    duration_seconds: 40,
    views_count: 2890,
    merchant: {
      id: 'm102-itwari',
      business_name: 'Mahalaxmi Silk Emporium',
      sector: 'FASHION',
      address: 'Itwari Cloth Market, Nagpur',
      distance_meters: 1200,
    },
    coupon: {
      id: 'c102-sarees',
      title: 'Flat ₹500 Off on Pure Silk Sarees',
      discount_type: 'FLAT_AMOUNT',
      discount_value: 500,
      min_order_amount: 3000,
      validity_days: 10,
    },
  },
  {
    id: 'f103-sample-nagpur',
    title: 'Freshly Baked Crusty Sourdough & Belgian Chocolate Brownies',
    video_url: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4',
    thumbnail_url: 'https://images.unsplash.com/photo-1509440159596-0249088772ff?w=600&auto=format&fit=crop',
    duration_seconds: 30,
    views_count: 850,
    merchant: {
      id: 'm103-dharampeth',
      business_name: 'The Crust Artisan Bakery',
      sector: 'FOOD',
      address: 'West High Court Road, Dharampeth, Nagpur',
      distance_meters: 2100,
    },
    coupon: {
      id: 'c103-bakery',
      title: 'Flat 40% Off on Gourmet Bakery Items',
      discount_type: 'PERCENTAGE',
      discount_value: 40,
      min_order_amount: 250,
      validity_days: 3,
    },
  },
]

export const FeedPage: React.FC = () => {
  const { t } = useTranslation()
  const { reels, isLoading, refetch } = useFeed()

  const displayReels = reels.length > 0 ? reels : FALLBACK_NAGPUR_REELS

  return (
    <div className="min-h-screen pb-24 pt-2 max-w-lg mx-auto px-4">
      {/* Top Filter Bar */}
      <div className="space-y-2.5 mb-4 sticky top-16 z-30 py-2 glass-panel rounded-2xl p-2.5 shadow-xl border border-slate-800/80">
        <RadiusFilter />
        <SectorFilter />
      </div>

      {/* Reel Feed List */}
      {isLoading ? (
        <div className="py-24 flex flex-col items-center justify-center gap-3">
          <RefreshCw className="h-8 w-8 text-amber-400 animate-spin" />
          <p className="text-xs text-slate-400 font-medium">Scanning nearby verified deals...</p>
        </div>
      ) : displayReels.length > 0 ? (
        <div className="space-y-6">
          {displayReels.map((reel) => (
            <ReelCard key={reel.id} reel={reel} />
          ))}
        </div>
      ) : (
        <div className="py-16 text-center rounded-3xl border border-slate-800 bg-slate-900/60 p-8 space-y-4">
          <div className="h-16 w-16 rounded-full bg-amber-500/10 text-amber-400 flex items-center justify-center mx-auto">
            <MapPin className="h-8 w-8" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white mb-1 font-heading">
              {t.empty_feed}
            </h3>
            <p className="text-xs text-slate-400">
              Expand your radius to 5km or 10km to explore more merchant discounts.
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <Sparkles className="h-4 w-4 mr-2 text-amber-400" />
            Refresh Nearby
          </Button>
        </div>
      )}
    </div>
  )
}
