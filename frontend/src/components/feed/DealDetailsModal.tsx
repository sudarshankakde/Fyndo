import React, { useRef, useState, useEffect } from 'react'
import {
  MapPin,
  Volume2,
  VolumeX,
  Play,
  Share2,
  Check,
  Sparkles,
  Store,
  Clock,
  ShieldCheck,
  Heart,
} from 'lucide-react'
import confetti from 'canvas-confetti'
import { Dialog } from '@/components/ui/Dialog'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { ReelItem } from '@/types/reel'
import { formatDiscount, formatDistance, formatRupees } from '@/utils/format'
import { useWallet } from '@/hooks/useWallet'
import { useAppSelector } from '@/store'
import { useNavigate } from 'react-router-dom'
import { feedService } from '@/services/feedService'
import { getSafeMediaUrl } from '@/utils/safeUrl'
import { ReelCommentsSection } from './ReelCommentsSection'

interface DealDetailsModalProps {
  reel: ReelItem | null
  isOpen: boolean
  onClose: () => void
}

export const DealDetailsModal: React.FC<DealDetailsModalProps> = ({
  reel,
  isOpen,
  onClose,
}) => {
  const navigate = useNavigate()
  const { isAuthenticated } = useAppSelector((state) => state.auth)
  const { claimCoupon, isClaiming } = useWallet()

  const videoRef = useRef<HTMLVideoElement>(null)
  const [isPlaying, setIsPlaying] = useState(true)
  const [isMuted, setIsMuted] = useState(false)
  const [isClaimed, setIsClaimed] = useState(false)
  const [isLiked, setIsLiked] = useState(false)
  const [likeCount, setLikeCount] = useState(0)
  const [hasRecordedView, setHasRecordedView] = useState(false)

  useEffect(() => {
    if (reel && isOpen) {
      setIsLiked(reel.is_liked || false)
      setLikeCount(reel.likes_count || 0)
      if (!hasRecordedView) {
        feedService.recordView(reel.id).catch(() => {})
        setHasRecordedView(true)
      }
    }
  }, [reel, isOpen, hasRecordedView])

  if (!reel) return null

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

  const toggleMute = () => {
    if (!videoRef.current) return
    videoRef.current.muted = !isMuted
    setIsMuted(!isMuted)
  }

  const handleLikeToggle = async () => {
    if (!isAuthenticated) {
      onClose()
      navigate('/login?next=/')
      return
    }
    const prevLiked = isLiked
    const prevCount = likeCount
    setIsLiked(!prevLiked)
    setLikeCount(prevLiked ? Math.max(0, prevCount - 1) : prevCount + 1)
    try {
      const res = await feedService.toggleLike(reel.id)
      setIsLiked(res.liked)
      setLikeCount(res.likes_count)
    } catch {
      setIsLiked(prevLiked)
      setLikeCount(prevCount)
    }
  }

  const handleClaim = async () => {
    if (!reel.coupon) return
    if (!isAuthenticated) {
      onClose()
      navigate('/login?next=/')
      return
    }
    try {
      await claimCoupon(reel.coupon.id)
      setIsClaimed(true)
      confetti({
        particleCount: 60,
        spread: 70,
        origin: { y: 0.6 },
        colors: ['#FF385C', '#10B981', '#F59E0B'],
      })
    } catch {
      setIsClaimed(true)
    }
  }

  const handleShareWhatsApp = () => {
    const text = encodeURIComponent(
      `Exclusive deal at ${reel.merchant.business_name}: "${reel.title}" on Fyndo!\nCheck it out: ${window.location.origin}/reel/${reel.id}`
    )
    window.open(`https://wa.me/?text=${text}`, '_blank')
  }

  const safeVideoUrl = getSafeMediaUrl(reel.video_url, reel.video_url)
  const safePosterUrl = getSafeMediaUrl(reel.thumbnail_url, reel.thumbnail_url)

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      className="max-w-4xl p-0 overflow-hidden bg-white border border-stone-200 shadow-2xl rounded-3xl"
    >
      <div className="grid grid-cols-1 md:grid-cols-2 max-h-[85vh] overflow-y-auto md:overflow-hidden">
        {/* Left: 9:16 Video Player Container */}
        <div className="relative aspect-[9/16] md:aspect-auto md:h-full bg-black flex items-center justify-center overflow-hidden min-h-[420px]">
          <video
            ref={videoRef}
            src={safeVideoUrl}
            poster={safePosterUrl}
            autoPlay
            loop
            playsInline
            muted={isMuted}
            onClick={togglePlay}
            className="w-full h-full object-cover cursor-pointer"
          />

          {!isPlaying && (
            <div
              onClick={togglePlay}
              className="absolute inset-0 flex items-center justify-center bg-black/40 cursor-pointer"
            >
              <div className="w-14 h-14 rounded-full bg-white/90 text-stone-900 flex items-center justify-center shadow-lg">
                <Play className="w-7 h-7 ml-1 fill-current" />
              </div>
            </div>
          )}

          {/* Sound & Like Floating Overlays */}
          <div className="absolute bottom-4 right-4 flex items-center gap-2">
            <button
              onClick={handleLikeToggle}
              className={`h-9 px-3 rounded-full backdrop-blur-md flex items-center gap-1.5 transition-colors text-xs font-bold ${
                isLiked ? 'bg-primary text-white' : 'bg-black/60 text-white hover:bg-black/80'
              }`}
            >
              <Heart className={`w-4 h-4 ${isLiked ? 'fill-white' : ''}`} />
              <span>{likeCount}</span>
            </button>
            <button
              onClick={toggleMute}
              className="h-9 w-9 rounded-full bg-black/60 backdrop-blur-md text-white flex items-center justify-center hover:bg-black/80 transition-colors"
            >
              {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Right: Store, Coupon Terms & Inquiries */}
        <div className="p-6 flex flex-col justify-between font-sans overflow-y-auto max-h-[85vh] space-y-4">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="px-3 py-1 rounded-full text-xs font-bold bg-amber-50 text-amber-800 border border-amber-200 uppercase tracking-wider">
                {reel.merchant.sector}
              </span>
              <span className="flex items-center gap-1 text-xs font-bold text-stone-600 bg-stone-100 px-3 py-1 rounded-full">
                <MapPin className="w-3.5 h-3.5 text-primary" />
                {formatDistance(reel.merchant.distance_meters)}
              </span>
            </div>

            {/* Merchant Identity */}
            <div>
              <div className="flex items-center gap-1.5">
                <h2 className="text-xl font-extrabold text-stone-900 tracking-tight font-display">
                  {reel.merchant.business_name}
                </h2>
                <ShieldCheck className="w-5 h-5 text-emerald-600 shrink-0" />
              </div>
              <p className="text-xs text-stone-500 mt-1 flex items-start gap-1">
                <Store className="w-3.5 h-3.5 text-stone-400 shrink-0 mt-0.5" />
                <span>{reel.merchant.address}</span>
              </p>
            </div>

            {/* Offer Details */}
            <div className="bg-stone-50 rounded-2xl p-4 border border-stone-200 space-y-2">
              {reel.coupon && (
                <div className="flex items-center gap-2">
                  <Badge variant="coral" className="text-sm px-3 py-1 font-extrabold">
                    {formatDiscount(reel.coupon.discount_type, reel.coupon.discount_value)}
                  </Badge>
                  <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
                    Verified Deal
                  </span>
                </div>
              )}
              <h3 className="text-sm font-extrabold text-stone-900 leading-snug">{reel.title}</h3>
              {reel.coupon && (
                <div className="text-xs text-stone-600 space-y-1 pt-1 border-t border-stone-200">
                  <p className="flex items-center justify-between">
                    <span>Min. Bill Amount:</span>
                    <span className="font-bold text-stone-900">
                      {formatRupees(reel.coupon.min_order_amount)}
                    </span>
                  </p>
                  <p className="flex items-center justify-between">
                    <span>Coupon Validity:</span>
                    <span className="font-bold text-stone-900 flex items-center gap-1">
                      <Clock className="w-3 h-3 text-stone-400" />
                      {reel.coupon.validity_days} days
                    </span>
                  </p>
                </div>
              )}
            </div>

            {/* Inquiries Section */}
            <ReelCommentsSection reelId={reel.id} allowComments={reel.allow_comments ?? true} />
          </div>

          {/* Action Footer */}
          <div className="space-y-2 pt-2 border-t border-stone-100">
            <Button
              variant={isClaimed ? 'outline' : 'primary'}
              disabled={isClaimed || isClaiming}
              onClick={handleClaim}
              className="w-full h-11 text-sm font-bold shadow-sm"
            >
              {isClaimed ? (
                <span className="flex items-center gap-1.5 text-emerald-700">
                  <Check className="w-4 h-4" />
                  Saved to Wallet (Present at Store)
                </span>
              ) : (
                <span className="flex items-center gap-1.5">
                  <Sparkles className="w-4 h-4" />
                  Claim Voucher to Wallet
                </span>
              )}
            </Button>

            <div className="grid grid-cols-2 gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  onClose()
                  navigate(`/store/${reel.merchant.id}`)
                }}
                className="text-xs font-semibold"
              >
                <Store className="w-3.5 h-3.5 mr-1" />
                Store Showcase
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleShareWhatsApp}
                className="text-xs font-semibold"
              >
                <Share2 className="w-3.5 h-3.5 mr-1 text-emerald-600" />
                Share WhatsApp
              </Button>
            </div>
          </div>
        </div>
      </div>
    </Dialog>
  )
}
