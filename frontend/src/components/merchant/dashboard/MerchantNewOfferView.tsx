import React, { useState } from 'react'
import { Film, AlertCircle, Info } from 'lucide-react'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { useFormValidation } from '@/hooks/useFormValidation'
import { offerCreateSchema } from '@/utils/validationSchemas'
import { merchantService } from '@/services/merchantService'
import { MerchantVideoUploader } from './MerchantVideoUploader'

interface MerchantNewOfferViewProps {
  onSuccess: (msg: string) => void
}

export const MerchantNewOfferView: React.FC<MerchantNewOfferViewProps> = ({ onSuccess }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [videoFile, setVideoFile] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)

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

  const handleFile = (file: File) => {
    setSelectedFile(file)
    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
    setVideoFile(file.name)
    setSubmitError(null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const isValid = await validateAll()
    if (!isValid) return

    setSubmitError(null)
    setIsSubmitting(true)

    try {
      let finalVideoUrl = 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/WeAreGoingOnBullrun.mp4'

      if (selectedFile) {
        finalVideoUrl = await merchantService.uploadMedia(selectedFile, 'reels')
      }

      await merchantService.createReel({
        title: values.title,
        video_url: finalVideoUrl,
        thumbnail_url: 'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=800&q=80',
        duration_seconds: 30,
        audio_type: 'CAMERA_MIC',
        coupon: {
          title: values.title,
          discount_type: values.discountType === 'FLAT' ? 'FLAT_AMOUNT' : 'PERCENTAGE',
          discount_value: values.discountValue,
          min_order_amount: values.minBillAmount,
          validity_days: values.validityDays,
          terms: 'Valid for in-store redemption',
        },
      })

      resetForm()
      setSelectedFile(null)
      setPreviewUrl(null)
      setVideoFile(null)
      onSuccess('Video offer submitted successfully! It has been placed in review.')
    } catch (err: any) {
      setSubmitError(err.message || 'Failed to submit video offer. Please check details.')
    } finally {
      setIsSubmitting(false)
    }
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

      {submitError && (
        <div className="p-3 rounded-lg border border-red-800/80 bg-red-950/60 text-red-300 text-xs font-mono flex items-center gap-2">
          <AlertCircle className="h-4 w-4 shrink-0 text-red-400" />
          <span>{submitError}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Video Reel Upload Box with Live Preview */}
        <MerchantVideoUploader
          selectedFile={selectedFile}
          previewUrl={previewUrl}
          videoFileName={videoFile}
          onSelectFile={handleFile}
          onUseSample={(name, url) => {
            setVideoFile(name)
            setPreviewUrl(url)
            setSelectedFile(null)
          }}
        />

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
