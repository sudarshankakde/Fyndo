import React, { useState } from 'react'
import { Film, CheckCircle2, AlertCircle, UploadCloud, Info } from 'lucide-react'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { useFormValidation } from '@/hooks/useFormValidation'
import { offerCreateSchema } from '@/utils/validationSchemas'

interface MerchantNewOfferViewProps {
  onSuccess: (msg: string) => void
}

export const MerchantNewOfferView: React.FC<MerchantNewOfferViewProps> = ({ onSuccess }) => {
  const [videoFile, setVideoFile] = useState<string | null>(null)

  const {
    values,
    errors,
    touched,
    isSubmitting,
    setIsSubmitting,
    handleChange,
    handleBlur,
    validateAll,
    resetForm,
  } = useFormValidation(
    {
      title: '',
      description: '',
      sector: 'FOOD',
      discountType: 'PERCENTAGE',
      discountValue: 40,
      minBillAmount: 200,
      validityDays: 3,
    },
    offerCreateSchema
  )

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const isValid = await validateAll()
    if (!isValid) return

    setIsSubmitting(true)
    setTimeout(() => {
      setIsSubmitting(false)
      resetForm()
      setVideoFile(null)
      onSuccess('Video offer submitted! It will be reviewed within 2 hours before going live.')
    }, 800)
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="pb-2 border-b border-stone-800">
        <h2 className="text-xl font-bold text-stone-100 font-display">
          Post In-Store Video & Offer
        </h2>
        <p className="text-xs text-stone-400 font-mono mt-0.5">
          Attach a time-restricted discount voucher to a 15–60s raw video reel.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Video Reel Simulator */}
        <div className="space-y-1.5">
          <label className="font-mono text-xs text-stone-300 block">
            15–60s Video Reel (Raw Store Audio Only)
          </label>
          <div className="border border-dashed border-stone-800 rounded-xl p-5 bg-stone-900/40 text-center space-y-2">
            <UploadCloud className="h-8 w-8 text-amber-400 mx-auto" />
            <p className="text-xs text-stone-300 font-medium">
              {videoFile ? `Selected: ${videoFile}` : 'Upload vertical 9:16 video reel'}
            </p>
            <p className="text-[11px] text-stone-400">
              Only authentic camera audio or voiceover. No copyrighted music.
            </p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setVideoFile('sitabuldi_sweets_reel_01.mp4')}
              className="text-xs font-mono"
            >
              {videoFile ? 'Change Reel' : 'Select Sample Video'}
            </Button>
          </div>
        </div>

        {/* Offer Title */}
        <div className="space-y-1">
          <label className="font-mono text-xs text-stone-300 block">Offer Headline</label>
          <Input
            placeholder="e.g. Hot Crispy Jalebis 40% Off this Sunday"
            value={values.title}
            onChange={(e) => handleChange('title', e.target.value)}
            onBlur={() => handleBlur('title')}
            error={touched.title ? errors.title : undefined}
          />
        </div>

        {/* Sector Selection */}
        <div className="space-y-1">
          <label className="font-mono text-xs text-stone-300 block">Retail Sector</label>
          <select
            value={values.sector}
            onChange={(e) => {
              const sec = e.target.value
              handleChange('sector', sec)
              if (sec === 'FOOD' && values.validityDays > 5) {
                handleChange('validityDays', 3)
              }
            }}
            onBlur={() => handleBlur('sector')}
            className="flex h-10 w-full rounded-lg border border-stone-800 bg-stone-900 px-3 py-2 text-sm text-stone-100 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-amber-500/60 font-sans"
          >
            <option value="FOOD">Food & Restaurants (Validity 2–5 days)</option>
            <option value="CLOTHES_FASHION">Clothes & Sarees (Validity max 15 days)</option>
            <option value="ELECTRONICS">Electronics (Validity max 15 days)</option>
            <option value="FOOTWEAR">Footwear & Shoes (Validity max 15 days)</option>
            <option value="PROPERTY">Showrooms / Real Estate (Validity up to 60 days)</option>
          </select>
        </div>

        {/* Discount Type & Value */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1">
            <label className="font-mono text-xs text-stone-300 block">Discount Type</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => handleChange('discountType', 'PERCENTAGE')}
                className={`py-2 rounded-lg text-xs font-mono font-medium border transition-colors ${
                  values.discountType === 'PERCENTAGE'
                    ? 'bg-amber-500 text-stone-950 border-amber-400 font-bold'
                    : 'bg-stone-900 text-stone-400 border-stone-800'
                }`}
              >
                Percentage (%)
              </button>
              <button
                type="button"
                onClick={() => handleChange('discountType', 'FLAT')}
                className={`py-2 rounded-lg text-xs font-mono font-medium border transition-colors ${
                  values.discountType === 'FLAT'
                    ? 'bg-amber-500 text-stone-950 border-amber-400 font-bold'
                    : 'bg-stone-900 text-stone-400 border-stone-800'
                }`}
              >
                Flat Rupee (₹)
              </button>
            </div>
          </div>

          <div className="space-y-1">
            <label className="font-mono text-xs text-stone-300 block">
              {values.discountType === 'PERCENTAGE' ? 'Discount Percentage (%)' : 'Discount Amount (₹)'}
            </label>
            <Input
              type="number"
              placeholder={values.discountType === 'PERCENTAGE' ? 'e.g. 40' : 'e.g. 200'}
              value={values.discountValue}
              onChange={(e) => handleChange('discountValue', Number(e.target.value))}
              onBlur={() => handleBlur('discountValue')}
              error={touched.discountValue ? errors.discountValue : undefined}
            />
          </div>
        </div>

        {/* Min Bill & Expiry Days */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1">
            <label className="font-mono text-xs text-stone-300 block">Minimum Bill (₹)</label>
            <Input
              type="number"
              placeholder="e.g. 200"
              value={values.minBillAmount}
              onChange={(e) => handleChange('minBillAmount', Number(e.target.value))}
              onBlur={() => handleBlur('minBillAmount')}
              error={touched.minBillAmount ? errors.minBillAmount : undefined}
            />
          </div>

          <div className="space-y-1">
            <label className="font-mono text-xs text-stone-300 block">
              Offer Validity Period (Days)
            </label>
            <Input
              type="number"
              value={values.validityDays}
              onChange={(e) => handleChange('validityDays', Number(e.target.value))}
              onBlur={() => handleBlur('validityDays')}
              error={touched.validityDays ? errors.validityDays : undefined}
            />
          </div>
        </div>

        {/* Sector Governance Hint */}
        <div className="p-3 rounded-lg border border-stone-800 bg-stone-950/70 flex items-start gap-2.5 text-xs text-stone-400">
          <Info className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
          <span>
            {values.sector === 'FOOD'
              ? 'Food offers expire within 2–5 days to keep promotions fresh and encourage prompt walk-ins.'
              : 'Apparel & electronics offers can be active for up to 15 days.'}
          </span>
        </div>

        <Button type="submit" variant="primary" size="lg" className="w-full" isLoading={isSubmitting}>
          <Film className="h-4 w-4 mr-2" />
          <span>Submit Video & Publish Offer</span>
        </Button>
      </form>
    </div>
  )
}
