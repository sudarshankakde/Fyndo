import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Check, X, RefreshCw, AlertCircle, CheckCircle2 } from 'lucide-react'
import { adminService, AdminPendingReel } from '@/services/adminService'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Dialog } from '@/components/ui/Dialog'
import { SECTOR_VALIDITY_CEILINGS } from '@/config/constants'
import { formatRupees } from '@/utils/format'
import { getSafeMediaUrl } from '@/utils/safeUrl'

export const AdminReelModerationView: React.FC = () => {
  const queryClient = useQueryClient()
  const [rejectingReel, setRejectingReel] = useState<AdminPendingReel | null>(null)
  const [rejectionReason, setRejectionReason] = useState('Copyrighted audio detected')
  const [customReason, setCustomReason] = useState('')

  const {
    data: reels = [],
    isLoading,
    refetch,
  } = useQuery<AdminPendingReel[]>({
    queryKey: ['admin-reels-moderation'],
    queryFn: () => adminService.getPendingReels(),
    refetchInterval: 30000,
  })

  const decideMutation = useMutation({
    mutationFn: ({
      reelId,
      decision,
      reason,
    }: {
      reelId: string
      decision: 'APPROVE' | 'REJECT'
      reason?: string
    }) => adminService.decideReel(reelId, decision, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-reels-moderation'] })
      queryClient.invalidateQueries({ queryKey: ['admin-stats'] })
      setRejectingReel(null)
      setCustomReason('')
    },
  })

  const handleApprove = (reel: AdminPendingReel) => {
    decideMutation.mutate({ reelId: reel.id, decision: 'APPROVE' })
  }

  const handleConfirmReject = () => {
    if (!rejectingReel) return
    const finalReason = customReason.trim() || rejectionReason
    decideMutation.mutate({
      reelId: rejectingReel.id,
      decision: 'REJECT',
      reason: finalReason,
    })
  }

  if (isLoading) {
    return (
      <div className="py-20 text-center space-y-3 font-sans">
        <RefreshCw className="w-8 h-8 text-primary animate-spin mx-auto" />
        <p className="text-xs text-stone-500 font-medium">Scanning video moderation queue...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6 font-sans text-stone-900">
      <div className="flex items-center justify-between pb-3 border-b border-stone-200">
        <div>
          <h2 className="text-xl font-extrabold text-stone-900 tracking-tight">Reel Video & Audio Review</h2>
          <p className="text-xs text-stone-500 mt-0.5">
            Audit vertical reels, camera audio policy, and sector discount validity caps.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()} className="text-xs font-bold gap-1.5">
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Queue ({reels.length})</span>
        </Button>
      </div>

      {reels.length === 0 ? (
        <div className="bg-white rounded-3xl border border-stone-200 p-12 text-center shadow-card space-y-3 max-w-md mx-auto">
          <div className="w-14 h-14 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto">
            <CheckCircle2 className="w-8 h-8" />
          </div>
          <h3 className="text-base font-extrabold text-stone-900">All Video Offers Cleared!</h3>
          <p className="text-xs text-stone-500 max-w-sm mx-auto leading-relaxed">
            Zero pending merchant reels in queue. Newly submitted store offers will appear here immediately.
          </p>
        </div>
      ) : (
        <div className="space-y-5">
          {reels.map((reel) => {
            const sectorCap = SECTOR_VALIDITY_CEILINGS[reel.sector] || 15
            const isCapCompliant = !reel.validity_days || reel.validity_days <= sectorCap
            const safeVideo = getSafeMediaUrl(reel.video_url, reel.video_url)
            const safePoster = getSafeMediaUrl(reel.thumbnail_url, reel.thumbnail_url)

            return (
              <div
                key={reel.id}
                className="bg-white rounded-3xl border border-stone-200/80 p-6 shadow-2xs grid grid-cols-1 md:grid-cols-12 gap-6 items-center"
              >
                {/* 9:16 Video Player */}
                <div className="md:col-span-5 aspect-[9/16] max-h-80 w-full rounded-2xl overflow-hidden bg-stone-950 relative mx-auto shadow-inner">
                  <video
                    src={safeVideo}
                    poster={safePoster}
                    controls
                    playsInline
                    className="w-full h-full object-cover"
                  />
                </div>

                {/* Offer Inspection Card */}
                <div className="md:col-span-7 space-y-4">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <Badge variant="outline">{reel.sector}</Badge>
                      <Badge variant="outline">{reel.city}</Badge>
                      <span className="text-[11px] font-bold text-stone-400 font-mono">
                        {reel.duration_seconds}s • Audio: {reel.audio_type}
                      </span>
                    </div>
                    <h3 className="text-lg font-black text-stone-900 tracking-tight">{reel.title}</h3>
                    <p className="text-xs font-bold text-stone-600 mt-0.5">Store: {reel.merchant_name}</p>
                  </div>

                  {/* Coupon Strip */}
                  {reel.coupon_title && (
                    <div className="bg-stone-50 rounded-2xl p-4 border border-stone-200 space-y-1.5 text-xs">
                      <div className="flex justify-between font-bold">
                        <span className="text-stone-500">Discount Offer:</span>
                        <span className="text-stone-900">{reel.coupon_title}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-stone-500">Min. Bill:</span>
                        <span className="font-bold text-stone-900">
                          {reel.min_order_amount ? formatRupees(reel.min_order_amount) : 'None'}
                        </span>
                      </div>
                      <div className="flex justify-between items-center pt-1 border-t border-stone-200">
                        <span className="text-stone-500">Sector Validity Limit:</span>
                        <span
                          className={`font-bold flex items-center gap-1 ${
                            isCapCompliant ? 'text-emerald-700' : 'text-red-600'
                          }`}
                        >
                          {isCapCompliant ? '✓ Within Cap' : '⚠ Exceeds Cap'} ({reel.validity_days}d / max {sectorCap}d)
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex gap-3 pt-2">
                    <Button
                      onClick={() => handleApprove(reel)}
                      variant="emerald"
                      disabled={decideMutation.isPending}
                      className="flex-1 gap-1.5 text-xs font-bold"
                    >
                      <Check className="w-4 h-4" />
                      <span>Approve & Publish</span>
                    </Button>
                    <Button
                      onClick={() => setRejectingReel(reel)}
                      variant="destructive"
                      disabled={decideMutation.isPending}
                      className="flex-1 gap-1.5 text-xs font-bold"
                    >
                      <X className="w-4 h-4" />
                      <span>Reject Offer</span>
                    </Button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Reject Modal */}
      {rejectingReel && (
        <Dialog
          isOpen={!!rejectingReel}
          onClose={() => setRejectingReel(null)}
          title={`Reject Reel: ${rejectingReel.title}`}
          description="Select reason for feedback to the shop owner."
        >
          <div className="space-y-4 pt-2 text-xs font-sans">
            <div>
              <label className="font-bold text-stone-700 block mb-1">Standard Reason</label>
              <select
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                className="w-full h-10 px-3 text-xs font-semibold rounded-xl border border-stone-200 bg-white"
              >
                <option value="Copyrighted audio detected">Copyrighted audio detected (Voice/Camera only)</option>
                <option value="Blurry or low-quality video">Blurry or low-quality video</option>
                <option value="Misleading discount terms">Misleading discount terms</option>
                <option value="Coupon validity exceeds sector limit">Coupon validity exceeds sector limit</option>
                <option value="Inappropriate store content">Inappropriate store content</option>
              </select>
            </div>

            <div>
              <label className="font-bold text-stone-700 block mb-1">Custom Feedback Note (Optional)</label>
              <input
                type="text"
                value={customReason}
                onChange={(e) => setCustomReason(e.target.value)}
                placeholder="Or specify exact issue for merchant..."
                className="w-full h-10 px-3 text-xs rounded-xl border border-stone-200"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" size="sm" onClick={() => setRejectingReel(null)}>
                Cancel
              </Button>
              <Button
                variant="destructive"
                size="sm"
                disabled={decideMutation.isPending}
                onClick={handleConfirmReject}
              >
                Confirm Rejection
              </Button>
            </div>
          </div>
        </Dialog>
      )}
    </div>
  )
}
