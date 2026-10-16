import React, { useState } from 'react'
import { Play, Check, X, RefreshCw, AlertCircle } from 'lucide-react'
import { AdminPendingReel, adminService } from '@/services/adminService'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'

interface AdminModerationDeskProps {
  reels: AdminPendingReel[]
  onRefresh: () => void
}

export const AdminModerationDesk: React.FC<AdminModerationDeskProps> = ({ reels, onRefresh }) => {
  const [processingId, setProcessingId] = useState<string | null>(null)

  const handleDecision = async (reelId: string, decision: 'APPROVE' | 'REJECT') => {
    setProcessingId(reelId)
    try {
      await adminService.decideReel(
        reelId,
        decision,
        decision === 'REJECT' ? 'Violated content or audio guidelines' : undefined
      )
      onRefresh()
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Decision failed')
    } finally {
      setProcessingId(null)
    }
  }

  if (reels.length === 0) {
    return (
      <div className="py-16 text-center rounded-3xl border border-slate-800 bg-slate-900/50 p-6 space-y-2">
        <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 text-emerald-400 mx-auto flex items-center justify-center font-bold text-xl">
          ✓
        </div>
        <h3 className="text-base font-bold text-white">Queue Empty</h3>
        <p className="text-xs text-slate-400 max-w-sm mx-auto">
          All submitted reels have been reviewed. New merchant uploads will appear here in real-time.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
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

          <div className="relative aspect-[9/16] max-h-64 rounded-2xl overflow-hidden bg-black mx-auto border border-slate-800">
            <video
              src={reel.video_url}
              poster={reel.thumbnail_url}
              controls
              className="w-full h-full object-cover"
            />
          </div>

          {reel.coupon_title && (
            <div className="p-3 rounded-2xl bg-slate-800/60 border border-slate-700/50 space-y-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-amber-400">
                Attached Coupon Offer
              </span>
              <p className="text-xs font-semibold text-white">{reel.coupon_title}</p>
              <p className="text-[11px] text-slate-400">
                Discount: {reel.discount_type === 'PERCENTAGE' ? `${reel.discount_value}%` : `₹${reel.discount_value}`} • Valid {reel.validity_days} days
              </p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3 pt-1">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleDecision(reel.id, 'REJECT')}
              disabled={processingId === reel.id}
              className="border-red-500/30 text-red-400 hover:bg-red-500/10"
            >
              <X className="h-4 w-4 mr-1.5" />
              Reject Reel
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => handleDecision(reel.id, 'APPROVE')}
              disabled={processingId === reel.id}
              className="bg-emerald-500 hover:bg-emerald-600 text-white"
            >
              <Check className="h-4 w-4 mr-1.5" />
              Approve & Publish
            </Button>
          </div>
        </div>
      ))}
    </div>
  )
}
