import React, { useRef, useState } from 'react'
import { MapPin, Volume2, VolumeX, Play, Eye, Share2, Check, Sparkles } from 'lucide-react'
import confetti from 'canvas-confetti'
import { ReelItem } from '@/types/reel'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { formatDistance, formatDiscount } from '@/utils/format'
import { useWallet } from '@/hooks/useWallet'
import { useAppSelector } from '@/store'
import { useNavigate } from 'react-router-dom'
import { getSafeMediaUrl } from '@/utils/safeUrl'

interface ReelCardProps {
  reel: ReelItem
  onSelect?: (reel: ReelItem) => void
}

export const ReelCard: React.FC<ReelCardProps> = ({ reel, onSelect }) => {
  const navigate = useNavigate()
  const { isAuthenticated } = useAppSelector((state) => state.auth)
  const { claimCoupon, isClaiming } = useWallet()

  const videoRef = useRef<HTMLVideoElement>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isMuted, setIsMuted] = useState(true)
  const [isClaimed, setIsClaimed] = useState(false)

  const handleMouseEnter = () => {
    if (videoRef.current) {
      videoRef.current.play().then(() => setIsPlaying(true)).catch(() => {})
    }
  }

  const handleMouseLeave = () => {
    if (videoRef.current) {
      videoRef.current.pause()
      setIsPlaying(false)
    }
  }

  const togglePlay = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (!videoRef.current) return
    if (isPlaying) {
      videoRef.current.pause()
      setIsPlaying(false)
    } else {
      videoRef.current.play().then(() => setIsPlaying(true)).catch(() => {})
    }
  }

  const toggleMute = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (!videoRef.current) return
    videoRef.current.muted = !isMuted
    setIsMuted(!isMuted)
  }

  const handleClaim = async (e: React.MouseEvent) => {
    e.stopPropagation()
    if (!reel.coupon) return
    if (!isAuthenticated) {
      navigate('/login?next=/')
      return
    }

    try {
      await claimCoupon(reel.coupon.id)
      setIsClaimed(true)
      confetti({
        particleCount: 50,
        spread: 60,
        origin: { y: 0.8 },
        colors: ['#FF385C', '#10B981', '#F59E0B'],
      })
    } catch {
      setIsClaimed(true)
    }
  }

  const handleShareWhatsApp = (e: React.MouseEvent) => {
    e.stopPropagation()
    const text = encodeURIComponent(
      `Check out this local deal at ${reel.merchant.business_name}: "${reel.title}" on Fyndo!\n${window.location.origin}/reel/${reel.id}`
    )
    window.open(`https://wa.me/?text=${text}`, '_blank')
  }

  const safeVideo = getSafeMediaUrl(reel.video_url, reel.video_url)
  const safePoster = getSafeMediaUrl(reel.thumbnail_url, reel.thumbnail_url)

  return (
    <div
      onClick={() => onSelect && onSelect(reel)}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className="group relative w-full aspect-[9/16] rounded-3xl overflow-hidden bg-stone-900 border border-stone-200/80 shadow-card hover:shadow-card-hover transition-all duration-300 cursor-pointer flex flex-col justify-between"
    >
      {/* Video Media Element */}
      <video
        ref={videoRef}
        src={safeVideo}
        poster={safePoster}
        playsInline
        loop
        muted={isMuted}
        onClick={togglePlay}
        className="absolute inset-0 w-full h-full object-cover transition-transform duration-500 group-hover:scale-[1.02]"
      />

      {/* Play / Pause Center Floating Overlay */}
      {!isPlaying && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/20 group-hover:bg-black/10 transition-colors pointer-events-none">
          <div className="w-12 h-12 rounded-full bg-white/90 text-stone-900 flex items-center justify-center shadow-md scale-95 group-hover:scale-110 transition-transform">
            <Play className="w-6 h-6 ml-0.5 fill-current" />
          </div>
        </div>
      )}

      {/* Top Floating Badges */}
      <div className="relative z-20 p-3 flex items-center justify-between pointer-events-none">
        <div className="flex items-center gap-1.5 pointer-events-auto">
          <span className="bg-white/95 backdrop-blur-md px-2.5 py-1 rounded-full text-[11px] font-bold text-stone-900 border border-stone-200 shadow-2xs flex items-center gap-1">
            <MapPin className="w-3 h-3 text-primary shrink-0" />
            {formatDistance(reel.merchant.distance_meters)}
          </span>
          <span className="bg-white/95 backdrop-blur-md px-2.5 py-1 rounded-full text-[10px] font-extrabold text-amber-800 border border-stone-200 shadow-2xs uppercase tracking-wider">
            {reel.merchant.sector}
          </span>
        </div>

        <div className="flex items-center gap-1.5 pointer-events-auto">
          <button
            onClick={handleShareWhatsApp}
            className="h-8 w-8 rounded-full bg-white/90 hover:bg-white backdrop-blur-md border border-stone-200 flex items-center justify-center text-stone-700 hover:text-emerald-600 transition-colors shadow-2xs"
            aria-label="Share deal"
          >
            <Share2 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={toggleMute}
            className="h-8 w-8 rounded-full bg-white/90 hover:bg-white backdrop-blur-md border border-stone-200 flex items-center justify-center text-stone-700 transition-colors shadow-2xs"
            aria-label={isMuted ? 'Unmute' : 'Mute'}
          >
            {isMuted ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Bottom Information & CTA Card */}
      <div className="relative z-20 p-3.5 bg-gradient-to-t from-black/90 via-black/50 to-transparent pt-14 space-y-2.5 pointer-events-auto">
        <div>
          <div className="flex items-center justify-between gap-1 mb-0.5">
            <h3 className="font-extrabold text-sm text-white tracking-tight drop-shadow-sm truncate">
              {reel.merchant.business_name}
            </h3>
            <span className="flex items-center gap-1 text-[10px] text-white/80 font-bold shrink-0">
              <Eye className="w-3 h-3" />
              {reel.views_count}
            </span>
          </div>
          <p className="text-xs text-white/90 line-clamp-1 leading-snug drop-shadow-xs font-medium">
            {reel.title}
          </p>
        </div>

        {/* Attached In-Store Coupon Strip */}
        {reel.coupon && (
          <div className="bg-white/95 backdrop-blur-md rounded-2xl p-2.5 border border-white/60 shadow-md space-y-2">
            <div className="flex items-center justify-between gap-1.5">
              <Badge variant="coral" className="text-xs font-extrabold py-0.5 px-2">
                {formatDiscount(reel.coupon.discount_type, reel.coupon.discount_value)}
              </Badge>
              <span className="text-[10px] text-stone-500 font-bold">
                {reel.coupon.validity_days}d valid
              </span>
            </div>

            <div className="flex items-center gap-1.5 pt-0.5">
              <Button
                size="sm"
                variant={isClaimed ? 'outline' : 'primary'}
                disabled={isClaimed || isClaiming}
                onClick={handleClaim}
                className="flex-1 h-8 text-xs font-bold py-0"
              >
                {isClaimed ? (
                  <span className="flex items-center justify-center gap-1 text-emerald-700">
                    <Check className="w-3.5 h-3.5" />
                    Saved
                  </span>
                ) : (
                  <span className="flex items-center justify-center gap-1">
                    <Sparkles className="w-3.5 h-3.5" />
                    Save Voucher
                  </span>
                )}
              </Button>

              <button
                type="button"
                onClick={() => onSelect && onSelect(reel)}
                className="h-8 px-2.5 rounded-full border border-stone-200 bg-stone-50 hover:bg-stone-100 text-stone-700 text-xs font-bold transition-colors shrink-0"
              >
                Details
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
