import React, { useState } from 'react'
import { Store, CheckCircle, AlertCircle } from 'lucide-react'
import { Dialog } from '@/components/ui/Dialog'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { merchantService, MerchantOnboardData } from '@/services/merchantService'

interface MerchantOnboardModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: (merchantId: string) => void
}

export const MerchantOnboardModal: React.FC<MerchantOnboardModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [formData, setFormData] = useState<MerchantOnboardData>({
    business_name: '',
    sector: 'FOOD',
    address_text: '',
    city: 'Nagpur',
    latitude: 21.1458,
    longitude: 79.0882,
    gstin: '',
    kyc_doc_url: 'https://res.cloudinary.com/fyndo/image/upload/kyc_mock.pdf',
  })
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.business_name.trim() || !formData.address_text.trim()) {
      setError('Please provide business name and store address')
      return
    }

    setIsLoading(true)
    setError(null)
    try {
      const res = await merchantService.onboardStore(formData)
      onSuccess(res.id)
      onClose()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Onboarding failed')
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
          <Store className="h-5 w-5 text-amber-400" />
          <span>Register Store on Fyndo</span>
        </div>
      }
      description="Register your physical local business to publish short reels and coupons."
    >
      {error && (
        <div className="mb-4 flex items-center gap-2 p-3 rounded-xl bg-red-500/15 border border-red-500/30 text-red-400 text-xs font-semibold">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-3.5">
        <div>
          <label className="text-xs font-semibold text-slate-300 mb-1 block">
            Business Name
          </label>
          <Input
            placeholder="e.g. Haldirams Sitabuldi / Bombay Dyeing"
            value={formData.business_name}
            onChange={(e) => setFormData({ ...formData, business_name: e.target.value })}
            required
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs font-semibold text-slate-300 mb-1 block">
              Business Sector
            </label>
            <select
              value={formData.sector}
              onChange={(e) => setFormData({ ...formData, sector: e.target.value })}
              className="w-full h-11 rounded-xl border border-slate-700 bg-slate-900/80 px-3 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-amber-500"
            >
              <option value="FOOD">Food & Sweets</option>
              <option value="FASHION">Fashion & Sarees</option>
              <option value="FOOTWEAR">Footwear</option>
              <option value="ELECTRONICS">Electronics</option>
              <option value="REAL_ESTATE">Real Estate</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300 mb-1 block">City</label>
            <select
              value={formData.city}
              onChange={(e) => setFormData({ ...formData, city: e.target.value })}
              className="w-full h-11 rounded-xl border border-slate-700 bg-slate-900/80 px-3 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-amber-500"
            >
              <option value="Nagpur">Nagpur (Beta)</option>
              <option value="Mumbai">Mumbai (Beta)</option>
            </select>
          </div>
        </div>

        <div>
          <label className="text-xs font-semibold text-slate-300 mb-1 block">
            Store Address
          </label>
          <Input
            placeholder="Shop No., Landmark, Sitabuldi / Dharampeth"
            value={formData.address_text}
            onChange={(e) => setFormData({ ...formData, address_text: e.target.value })}
            required
          />
        </div>

        <div>
          <label className="text-xs font-semibold text-slate-300 mb-1 block">
            GSTIN (Optional)
          </label>
          <Input
            placeholder="27ABCDE1234F1Z5"
            value={formData.gstin || ''}
            onChange={(e) => setFormData({ ...formData, gstin: e.target.value })}
          />
        </div>

        <Button type="submit" variant="gold" size="lg" className="w-full mt-3" isLoading={isLoading}>
          <CheckCircle className="h-4 w-4 mr-2" />
          <span>Register Store Profile</span>
        </Button>
      </form>
    </Dialog>
  )
}
