import React, { useState } from 'react'
import { Plus, Store, Phone, MapPin, KeyRound, Check, X } from 'lucide-react'
import { AdminMerchantItem, CreateMerchantPayload, adminService } from '@/services/adminService'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'

interface AdminMerchantsDeskProps {
  merchants: AdminMerchantItem[]
  onRefresh: () => void
}

export const AdminMerchantsDesk: React.FC<AdminMerchantsDeskProps> = ({ merchants, onRefresh }) => {
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState<CreateMerchantPayload>({
    business_name: '',
    owner_phone: '+91',
    sector: 'FOOD',
    address_text: '',
    city: 'Nagpur',
    latitude: 21.1458,
    longitude: 79.0882,
    staff_name: 'Store Cashier',
    staff_pin: '123456',
  })
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    try {
      await adminService.createMerchant(form)
      setShowModal(false)
      onRefresh()
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to create merchant')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-white">Registered Stores</h2>
          <p className="text-xs text-slate-400">Total {merchants.length} partner stores</p>
        </div>
        <Button size="sm" onClick={() => setShowModal(true)} className="bg-sky-500 hover:bg-sky-600 text-white">
          <Plus className="h-4 w-4 mr-1" />
          Add Store
        </Button>
      </div>

      <div className="grid gap-3">
        {merchants.map((m) => (
          <div
            key={m.id}
            className="p-4 rounded-2xl border border-slate-800 bg-slate-900/80 hover:bg-slate-900 transition-colors space-y-3"
          >
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-bold text-base text-white">{m.business_name}</h3>
                  <Badge variant={m.kyc_status === 'APPROVED' ? 'success' : 'amber'} className="text-[10px]">
                    {m.kyc_status}
                  </Badge>
                </div>
                <p className="text-xs text-slate-400 flex items-center gap-1 mt-0.5">
                  <MapPin className="h-3 w-3 text-slate-500" />
                  {m.address_text}, {m.city}
                </p>
              </div>
              <Badge variant="outline" className="text-xs">
                {m.sector}
              </Badge>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs pt-2 border-t border-slate-800/60">
              <div className="flex items-center gap-1.5 text-slate-300">
                <Phone className="h-3.5 w-3.5 text-sky-400" />
                <span>Owner: {m.owner_phone}</span>
              </div>
              <div className="flex items-center gap-1.5 text-slate-300">
                <KeyRound className="h-3.5 w-3.5 text-amber-400" />
                <span>Staff: {m.staff_name || 'No staff'}</span>
              </div>
              <div className="text-slate-400 text-right md:text-left">
                <span>{m.reels_count} Active Reels</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {showModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-3xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-lg text-white">Onboard New Store</h3>
              <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-white">
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Store Name</label>
                <input
                  required
                  value={form.business_name}
                  onChange={(e) => setForm({ ...form, business_name: e.target.value })}
                  placeholder="Haldiram's Sitabuldi"
                  className="w-full p-2.5 rounded-xl bg-slate-800 border border-slate-700 text-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Owner Phone</label>
                  <input
                    required
                    value={form.owner_phone}
                    onChange={(e) => setForm({ ...form, owner_phone: e.target.value })}
                    placeholder="+919822011111"
                    className="w-full p-2.5 rounded-xl bg-slate-800 border border-slate-700 text-white"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Sector</label>
                  <select
                    value={form.sector}
                    onChange={(e) => setForm({ ...form, sector: e.target.value })}
                    className="w-full p-2.5 rounded-xl bg-slate-800 border border-slate-700 text-white"
                  >
                    <option value="FOOD">FOOD</option>
                    <option value="FASHION">FASHION</option>
                    <option value="FOOTWEAR">FOOTWEAR</option>
                    <option value="ELECTRONICS">ELECTRONICS</option>
                    <option value="REAL_ESTATE">REAL_ESTATE</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Address Text</label>
                <input
                  required
                  value={form.address_text}
                  onChange={(e) => setForm({ ...form, address_text: e.target.value })}
                  placeholder="Main Road, Sitabuldi, Nagpur"
                  className="w-full p-2.5 rounded-xl bg-slate-800 border border-slate-700 text-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Staff Name</label>
                  <input
                    value={form.staff_name}
                    onChange={(e) => setForm({ ...form, staff_name: e.target.value })}
                    placeholder="Sanjay Cashier"
                    className="w-full p-2.5 rounded-xl bg-slate-800 border border-slate-700 text-white"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">6-digit Staff PIN</label>
                  <input
                    maxLength={6}
                    value={form.staff_pin}
                    onChange={(e) => setForm({ ...form, staff_pin: e.target.value })}
                    placeholder="123456"
                    className="w-full p-2.5 rounded-xl bg-slate-800 border border-slate-700 text-white"
                  />
                </div>
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <Button variant="ghost" type="button" onClick={() => setShowModal(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={isSubmitting} className="bg-sky-500 hover:bg-sky-600 text-white">
                  {isSubmitting ? 'Registering...' : 'Register Store'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
