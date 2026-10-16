import React, { useState } from 'react'
import { Plus, Film, Tag, Clock, Eye, X } from 'lucide-react'
import { AdminPendingReel, AdminMerchantItem, CreateReelPayload, adminService } from '@/services/adminService'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'

interface AdminReelsDeskProps {
  reels: AdminPendingReel[]
  merchants: AdminMerchantItem[]
  onRefresh: () => void
}

export const AdminReelsDesk: React.FC<AdminReelsDeskProps> = ({ reels, merchants, onRefresh }) => {
  const [showModal, setShowModal] = useState(false)
  const [statusFilter, setStatusFilter] = useState<string>('ALL')
  const [form, setForm] = useState<CreateReelPayload>({
    merchant_id: merchants[0]?.id || '',
    title: '',
    video_url: 'https://res.cloudinary.com/fyndo/video/sample_food_reel.mp4',
    thumbnail_url: 'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=600&q=80',
    duration_seconds: 30,
    coupon_title: '',
    discount_type: 'PERCENTAGE',
    discount_value: 20,
    validity_days: 5,
    min_order_amount: 0,
  })
  const [isSubmitting, setIsSubmitting] = useState(false)

  const filteredReels = reels.filter((r) => {
    if (statusFilter === 'ALL') return true
    return r.status === statusFilter
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.merchant_id && merchants.length > 0) {
      form.merchant_id = merchants[0].id
    }
    setIsSubmitting(true)
    try {
      await adminService.createReel(form)
      setShowModal(false)
      onRefresh()
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to publish reel')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {['ALL', 'APPROVED', 'PENDING_MODERATION', 'REJECTED'].map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1 rounded-xl text-xs font-semibold transition-colors ${
                statusFilter === s
                  ? 'bg-amber-400 text-slate-900'
                  : 'bg-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              {s.replace('_', ' ')}
            </button>
          ))}
        </div>
        <Button size="sm" onClick={() => setShowModal(true)} className="bg-purple-500 hover:bg-purple-600 text-white">
          <Plus className="h-4 w-4 mr-1" />
          Publish Reel
        </Button>
      </div>

      <div className="grid gap-3">
        {filteredReels.map((r) => (
          <div
            key={r.id}
            className="p-3.5 rounded-2xl border border-slate-800 bg-slate-900/80 flex items-center gap-3.5"
          >
            <img
              src={r.thumbnail_url}
              alt={r.title}
              className="w-16 h-24 rounded-xl object-cover border border-slate-700 shrink-0"
            />
            <div className="flex-1 min-w-0 space-y-1">
              <div className="flex items-center gap-2">
                <Badge
                  variant={
                    r.status === 'APPROVED' ? 'success' : r.status === 'REJECTED' ? 'destructive' : 'amber'
                  }
                  className="text-[10px]"
                >
                  {r.status}
                </Badge>
                <span className="text-[11px] text-slate-400">{r.duration_seconds}s</span>
              </div>
              <h4 className="font-bold text-sm text-white truncate">{r.title}</h4>
              <p className="text-xs text-amber-400">{r.merchant_name}</p>
              {r.coupon_title && (
                <div className="flex items-center gap-1.5 text-[11px] text-slate-300">
                  <Tag className="h-3 w-3 text-sky-400" />
                  <span>{r.coupon_title} ({r.discount_value}%)</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {showModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-3xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-lg text-white">Direct Reel Publication</h3>
              <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-white">
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Target Merchant</label>
                <select
                  value={form.merchant_id}
                  onChange={(e) => setForm({ ...form, merchant_id: e.target.value })}
                  className="w-full p-2.5 rounded-xl bg-slate-800 border border-slate-700 text-white"
                >
                  {merchants.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.business_name} ({m.city})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Reel Title</label>
                <input
                  required
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  placeholder="Fresh Evening Snack Fest 20% Off"
                  className="w-full p-2.5 rounded-xl bg-slate-800 border border-slate-700 text-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Offer Title</label>
                  <input
                    required
                    value={form.coupon_title}
                    onChange={(e) => setForm({ ...form, coupon_title: e.target.value })}
                    placeholder="Evening Snack Fest"
                    className="w-full p-2.5 rounded-xl bg-slate-800 border border-slate-700 text-white"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Discount %</label>
                  <input
                    type="number"
                    value={form.discount_value}
                    onChange={(e) => setForm({ ...form, discount_value: Number(e.target.value) })}
                    className="w-full p-2.5 rounded-xl bg-slate-800 border border-slate-700 text-white"
                  />
                </div>
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <Button variant="ghost" type="button" onClick={() => setShowModal(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={isSubmitting} className="bg-purple-500 hover:bg-purple-600 text-white">
                  {isSubmitting ? 'Publishing...' : 'Publish to Feed'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
