import React, { useState } from 'react'
import { Video, Sparkles, AlertCircle, CheckCircle } from 'lucide-react'
import { Dialog } from '@/components/ui/Dialog'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { merchantService, ReelCreatePayload } from '@/services/merchantService'

interface ReelUploadModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: (reelId: string) => void
  storeSector?: string
}

export const ReelUploadModal: React.FC<ReelUploadModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  storeSector = 'FOOD',
}) => {
  const maxDays = storeSector === 'FOOD' ? 5 : 15

  const [formData, setFormData] = useState<ReelCreatePayload>({
    title: '',
    video_url: 'https://res.cloudinary.com/fyndo/video/upload/sample_reel.mp4',
    thumbnail_url: 'https://res.cloudinary.com/fyndo/image/upload/sample_thumb.webp',
    duration_seconds: 30,
    audio_type: 'CAMERA_MIC',
    coupon: {
      title: '',
      discount_type: 'PERCENTAGE',
      discount_value: 20,
      min_order_amount: 200,
      validity_days: maxDays > 5 ? 7 : 3,
    },
  })
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.title.trim() || !formData.coupon.title.trim()) {
      setError('Please provide reel title and coupon offer title')
      return
    }

    if (formData.coupon.validity_days > maxDays) {
      setError(`${storeSector} coupons cannot exceed ${maxDays} days validity`)
      return
    }

    setIsLoading(true)
    setError(null)
    try {
      const res = await merchantService.createReel(formData)
      onSuccess(res.reel_id)
      onClose()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to publish reel')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title={
        <div className="flex items-center gap-2">
          <Video className="h-5 w-5 text-amber-400" />
          <span>Publish Reel & Sector Coupon</span>
        </div>
      }
      description="Vertical 15-60s reels with in-store discount incentives (Queued for Super Admin approval)."
    >
      {error && (
        <div className="mb-4 flex items-center gap-2 p-3 rounded-xl bg-red-500/15 border border-red-500/30 text-red-400 text-xs font-semibold">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="text-xs font-semibold text-slate-300 mb-1 block">
            Reel Caption / Title
          </label>
          <Input
            placeholder="e.g. Fresh Hot Jalebis & Fafda 40% Off this Sunday!"
            value={formData.title}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            required
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs font-semibold text-slate-300 mb-1 block">Duration</label>
            <select
              value={formData.duration_seconds}
              onChange={(e) =>
                setFormData({ ...formData, duration_seconds: Number(e.target.value) })
              }
              className="w-full h-11 rounded-xl border border-slate-700 bg-slate-900/80 px-3 text-sm text-slate-200 focus:ring-2 focus:ring-amber-500"
            >
              <option value={15}>15 Seconds</option>
              <option value={30}>30 Seconds</option>
              <option value={45}>45 Seconds</option>
              <option value={60}>60 Seconds</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300 mb-1 block">Audio Policy</label>
            <select
              value={formData.audio_type}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  audio_type: e.target.value as 'CAMERA_MIC' | 'VOICEOVER',
                })
              }
              className="w-full h-11 rounded-xl border border-slate-700 bg-slate-900/80 px-3 text-sm text-slate-200 focus:ring-2 focus:ring-amber-500"
            >
              <option value="CAMERA_MIC">Camera Mic (Raw)</option>
              <option value="VOICEOVER">Voiceover (Owner)</option>
            </select>
          </div>
        </div>

        {/* Attached Coupon Definition */}
        <div className="p-3.5 rounded-2xl border border-amber-500/20 bg-amber-500/5 space-y-3">
          <div className="flex items-center gap-1.5 text-xs font-bold text-amber-400">
            <Sparkles className="h-4 w-4" />
            <span>Attached Store Coupon Offer</span>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300 mb-1 block">Offer Title</label>
            <Input
              placeholder="e.g. Flat 40% Off on All Traditional Sweets"
              value={formData.coupon.title}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  coupon: { ...formData.coupon, title: e.target.value },
                })
              }
              required
            />
          </div>

          <div className="grid grid-cols-3 gap-2">
            <div>
              <label className="text-[11px] font-semibold text-slate-400 mb-1 block">Type</label>
              <select
                value={formData.coupon.discount_type}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    coupon: {
                      ...formData.coupon,
                      discount_type: e.target.value as 'PERCENTAGE' | 'FLAT_AMOUNT',
                    },
                  })
                }
                className="w-full h-10 rounded-xl border border-slate-700 bg-slate-900 px-2 text-xs text-slate-200"
              >
                <option value="PERCENTAGE">Percent (%)</option>
                <option value="FLAT_AMOUNT">Flat (₹)</option>
              </select>
            </div>

            <div>
              <label className="text-[11px] font-semibold text-slate-400 mb-1 block">Value</label>
              <Input
                type="number"
                value={formData.coupon.discount_value}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    coupon: { ...formData.coupon, discount_value: Number(e.target.value) },
                  })
                }
                className="h-10 text-xs"
                required
              />
            </div>

            <div>
              <label className="text-[11px] font-semibold text-slate-400 mb-1 block">
                Validity (Max {maxDays}d)
              </label>
              <Input
                type="number"
                max={maxDays}
                min={1}
                value={formData.coupon.validity_days}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    coupon: { ...formData.coupon, validity_days: Number(e.target.value) },
                  })
                }
                className="h-10 text-xs"
                required
              />
            </div>
          </div>
        </div>

        <Button type="submit" variant="gold" size="lg" className="w-full mt-2" isLoading={isLoading}>
          <CheckCircle className="h-4 w-4 mr-2" />
          <span>Submit for Super Admin Review</span>
        </Button>
      </form>
    </Dialog>
  )
}
