import React, { useRef, useState } from 'react'
import { MapPin, Volume2, VolumeX, Play, Eye } from 'lucide-react'
import { ReelItem } from '@/types/reel'
import { CouponBanner } from './CouponBanner'
import { Badge } from '@/components/ui/Badge'
import { useTranslation } from '@/hooks/useTranslation'

interface ReelCardProps {
  reel: ReelItem
  isActive?: boolean
}

export const ReelCard: React.FC<ReelCardProps> = ({ reel }) => {
  const { t } = useTranslation()
  const videoRef = useRef<HTMLVideoElement>(null)
  const [isPlaying, setIsPlaying] = useState(true)
  const [isMuted, setIsMuted] = useState(true)

  const togglePlay = () => {
    if (!videoRef.current) return
    if (isPlaying) {
      videoRef.current.pause()
      setIsPlaying(false)
    } else {
      videoRef.current.play().catch(() => {})
      setIsPlaying(true)
    }
  }

  const toggleMute = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (!videoRef.current) return
    videoRef.current.muted = !isMuted
    setIsMuted(!isMuted)
  }

  const formattedDistance =
    reel.merchant.distance_meters < 1000
      ? `${reel.merchant.distance_meters}m`
      : `${(reel.merchant.distance_meters / 1000).toFixed(1)}km`

  return (
    <div className="relative w-full max-w-sm sm:max-w-md mx-auto aspect-reel rounded-3xl overflow-hidden bg-slate-950 border border-slate-800 shadow-2xl shadow-black/80 select-none group">
      {/* Video Element */}
      <video
        ref={videoRef}
        src={reel.video_url}
        poster={reel.thumbnail_url}
        playsInline
        loop
        muted={isMuted}
        autoPlay
        onClick={togglePlay}
        className="w-full h-full object-cover cursor-pointer"
      />

      {/* Play/Pause Center Indicator (When paused) */}
      {!isPlaying && (
        <div
          onClick={togglePlay}
          className="absolute inset-0 flex items-center justify-center bg-black/40 backdrop-blur-[2px] cursor-pointer"
        >
          <div className="h-16 w-16 rounded-full bg-amber-500/90 text-slate-950 flex items-center justify-center shadow-xl shadow-amber-500/30 scale-110 transition-transform">
            <Play className="h-8 w-8 ml-1 fill-current" />
          </div>
        </div>
      )}

      {/* Top Header Bar Overlay */}
      <div className="absolute top-3 left-3 right-3 flex items-center justify-between z-20 pointer-events-none">
        <div className="flex items-center gap-1.5 pointer-events-auto">
          <Badge variant="amber" className="glass-pill border-amber-500/40 font-bold text-xs py-1">
            <MapPin className="h-3 w-3 mr-1 text-amber-400" />
            {formattedDistance} {t.away}
          </Badge>
          <Badge variant="outline" className="glass-pill border-slate-700/60 text-[11px] uppercase">
            {reel.merchant.sector}
          </Badge>
        </div>

        <button
          onClick={toggleMute}
          className="h-9 w-9 rounded-full glass-pill flex items-center justify-center text-white pointer-events-auto hover:bg-slate-800 transition-colors shadow-lg"
          aria-label={isMuted ? 'Unmute' : 'Mute'}
        >
          {isMuted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
        </button>
      </div>

      {/* Bottom Information Overlay */}
      <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-slate-950 via-slate-950/80 to-transparent pt-16 z-20 space-y-3 pointer-events-auto">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-bold text-base text-white font-heading tracking-wide">
              {reel.merchant.business_name}
            </span>
            <span className="flex items-center gap-1 text-[11px] text-slate-400">
              <Eye className="h-3 w-3" />
              {reel.views_count}
            </span>
          </div>
          <p className="text-xs text-slate-300 line-clamp-2 leading-relaxed">
            {reel.title}
          </p>
          <p className="text-[11px] text-slate-400 truncate mt-0.5">
            {reel.merchant.address}
          </p>
        </div>

        {/* Attached In-Store Coupon Banner */}
        {reel.coupon && <CouponBanner coupon={reel.coupon} />}
      </div>
    </div>
  )
}
