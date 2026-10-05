import React, { useEffect, useState } from 'react'
import { ShieldCheck, Check, X, RefreshCw, AlertCircle, Play } from 'lucide-react'
import { adminService, AdminPendingReel } from '@/services/adminService'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { useTranslation } from '@/hooks/useTranslation'

export const AdminPage: React.FC = () => {
  const { t } = useTranslation()
  const [reels, setReels] = useState<AdminPendingReel[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [decisionProcessingId, setDecisionProcessingId] = useState<string | null>(null)

  const loadPendingReels = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await adminService.getPendingReels()
      setReels(data)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load moderation queue')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadPendingReels()
  }, [])

  const handleDecision = async (reelId: string, decision: 'APPROVE' | 'REJECT') => {
    setDecisionProcessingId(reelId)
    try {
      await adminService.decideReel(
        reelId,
        decision,
        decision === 'REJECT' ? 'Violated copyright/audio guidelines' : undefined
      )
      setReels((prev) => prev.filter((r) => r.id !== reelId))
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Decision failed')
    } finally {
      setDecisionProcessingId(null)
    }
  }

  return (
    <div className="min-h-screen pb-24 pt-4 max-w-2xl mx-auto px-4 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between gap-2">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="amber" className="text-xs font-bold py-0.5">
              Super Admin Moderation
            </Badge>
            <span className="text-xs text-slate-400">Content Integrity</span>
          </div>
          <h1 className="text-2xl font-extrabold text-white font-heading">{t.admin_desk}</h1>
          <p className="text-xs text-slate-400">
            Mandatory review of merchant reels before publication to local discovery feeds.
          </p>
        </div>

        <Button variant="ghost" size="sm" onClick={loadPendingReels} className="text-slate-400">
          <RefreshCw className="h-3.5 w-3.5 mr-1" />
          Refresh
        </Button>
      </div>

      {error && (
        <div className="p-3.5 rounded-xl bg-red-500/15 border border-red-500/30 text-red-400 text-xs font-semibold flex items-center gap-2">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {isLoading ? (
        <div className="py-20 flex flex-col items-center justify-center gap-3">
          <RefreshCw className="h-8 w-8 text-amber-400 animate-spin" />
          <p className="text-xs text-slate-400">Loading pending queue...</p>
        </div>
      ) : reels.length > 0 ? (
        <div className="space-y-5">
          {reels.map((reel) => (
            <div
              key={reel.id}
              className="rounded-3xl border border-slate-800 bg-slate-900/90 p-4 shadow-xl space-y-3.5"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-bold text-base text-white">{reel.title}</h3>
                  <p className="text-xs text-amber-400 font-semibold">{reel.merchant_name}</p>
                  <p className="text-[11px] text-slate-400">
                    {reel.city} • Sector: {reel.sector}
                  </p>
                </div>
                <Badge variant="outline" className="text-[11px]">
                  {reel.audio_type}
                </Badge>
              </div>

              {/* Video Player */}
              <div className="relative aspect-video max-h-60 rounded-2xl overflow-hidden bg-black border border-slate-800">
                <video
                  src={reel.video_url}
                  poster={reel.thumbnail_url}
                  controls
                  className="w-full h-full object-contain"
                />
              </div>

              {/* Attached Coupon Review */}
              {reel.coupon_title && (
                <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 text-xs flex items-center justify-between">
                  <div>
                    <span className="font-bold text-white block">{reel.coupon_title}</span>
                    <span className="text-[11px] text-slate-400">
                      Discount: {reel.discount_value}% | Validity: {reel.validity_days} days
                    </span>
                  </div>
                  <Badge variant="amber">Offer Attached</Badge>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex items-center gap-2.5 pt-1">
                <Button
                  variant="primary"
                  size="md"
                  className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white font-bold"
                  disabled={decisionProcessingId === reel.id}
                  onClick={() => handleDecision(reel.id, 'APPROVE')}
                >
                  <Check className="h-4 w-4 mr-1.5" />
                  Approve to Feed
                </Button>
                <Button
                  variant="destructive"
                  size="md"
                  className="flex-1 font-bold"
                  disabled={decisionProcessingId === reel.id}
                  onClick={() => handleDecision(reel.id, 'REJECT')}
                >
                  <X className="h-4 w-4 mr-1.5" />
                  Reject Reel
                </Button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="py-20 text-center rounded-3xl border border-slate-800 bg-slate-900/40 p-8 space-y-3">
          <div className="h-14 w-14 rounded-full bg-emerald-500/10 text-emerald-400 flex items-center justify-center mx-auto">
            <ShieldCheck className="h-7 w-7" />
          </div>
          <h3 className="text-base font-bold text-white font-heading">
            Moderation Queue is Clear!
          </h3>
          <p className="text-xs text-slate-400 max-w-xs mx-auto">
            All submitted merchant reels have been reviewed and published to the live feed.
          </p>
        </div>
      )}
    </div>
  )
}
