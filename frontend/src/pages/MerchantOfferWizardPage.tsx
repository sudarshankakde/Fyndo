import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle2, AlertCircle, ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { merchantService } from '@/services/merchantService'
import { SECTOR_VALIDITY_CEILINGS } from '@/config/constants'
import { OfferVideoStep } from '@/components/merchant/OfferVideoStep'
import { OfferCouponStep } from '@/components/merchant/OfferCouponStep'

export const MerchantOfferWizardPage: React.FC = () => {
  const navigate = useNavigate()

  const [step, setStep] = useState<1 | 2>(1)
  const [videoFile, setVideoFile] = useState<File | null>(null)
  const [videoUrl, setVideoUrl] = useState('')
  const [thumbnailUrl, setThumbnailUrl] = useState('')
  const [durationSec, setDurationSec] = useState(0)
  const [audioType, setAudioType] = useState<'CAMERA_MIC' | 'VOICEOVER'>('CAMERA_MIC')
  const [musicAck, setMusicAck] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [isUploading, setIsUploading] = useState(false)

  // Coupon state
  const [title, setTitle] = useState('')
  const [discountType, setDiscountType] = useState<'PERCENTAGE' | 'FLAT_AMOUNT' | 'BOGO'>('PERCENTAGE')
  const [discountValue, setDiscountValue] = useState(20)
  const [minOrder, setMinOrder] = useState(300)
  const sectorCeiling = SECTOR_VALIDITY_CEILINGS['FOOD'] || 5
  const [validityDays, setValidityDays] = useState(sectorCeiling)
  const [terms, setTerms] = useState('Valid for dine-in and takeaway. Not combinable with other offers.')

  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isDone, setIsDone] = useState(false)

  const handleSubmit = async () => {
    setIsSubmitting(true)
    setErrorMessage(null)

    try {
      await merchantService.createReel({
        title: title.trim(),
        video_url: videoUrl,
        thumbnail_url: thumbnailUrl,
        duration_seconds: durationSec || 30,
        audio_type: audioType,
        coupon: {
          title: title.trim(),
          discount_type: discountType,
          discount_value: discountValue,
          min_order_amount: minOrder,
          validity_days: validityDays,
          terms,
        },
      })
      setIsDone(true)
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to submit store offer.')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (isDone) {
    return (
      <div className="max-w-md mx-auto bg-white rounded-3xl border border-stone-200 p-8 shadow-card text-center space-y-4 my-8 font-sans">
        <div className="w-16 h-16 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto">
          <CheckCircle2 className="w-9 h-9" />
        </div>
        <h1 className="text-xl font-extrabold text-stone-900">Offer Submitted for Review!</h1>
        <p className="text-xs text-stone-500 leading-relaxed">
          Our admin team reviews store videos within 2 hours. Once approved, your video will automatically appear to nearby customers.
        </p>
        <Button onClick={() => navigate('/merchant')} className="w-full">
          Back to Dashboard
        </Button>
      </div>
    )
  }

  return (
    <div className="max-w-xl mx-auto space-y-6 font-sans">
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/merchant')}
          className="flex items-center gap-1.5 text-xs font-bold text-stone-500 hover:text-stone-900"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Cancel</span>
        </button>
        <span className="text-xs font-bold text-primary">Step {step} of 2</span>
      </div>

      {errorMessage && (
        <div className="p-3.5 rounded-2xl bg-red-50 border border-red-200 text-red-700 text-xs font-medium flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
          <span>{errorMessage}</span>
        </div>
      )}

      <div className="bg-white rounded-3xl border border-stone-200 p-6 sm:p-8 shadow-card space-y-6">
        {step === 1 ? (
          <OfferVideoStep
            videoFile={videoFile}
            setVideoFile={setVideoFile}
            videoUrl={videoUrl}
            setVideoUrl={setVideoUrl}
            setThumbnailUrl={setThumbnailUrl}
            durationSec={durationSec}
            setDurationSec={setDurationSec}
            audioType={audioType}
            setAudioType={setAudioType}
            musicAck={musicAck}
            setMusicAck={setMusicAck}
            uploadProgress={uploadProgress}
            setUploadProgress={setUploadProgress}
            isUploading={isUploading}
            setIsUploading={setIsUploading}
            setErrorMessage={setErrorMessage}
            onNext={() => setStep(2)}
          />
        ) : (
          <OfferCouponStep
            title={title}
            setTitle={setTitle}
            discountType={discountType}
            setDiscountType={setDiscountType}
            discountValue={discountValue}
            setDiscountValue={setDiscountValue}
            minOrder={minOrder}
            setMinOrder={setMinOrder}
            validityDays={validityDays}
            setValidityDays={setValidityDays}
            sectorCeiling={sectorCeiling}
            terms={terms}
            setTerms={setTerms}
            isSubmitting={isSubmitting}
            onBack={() => setStep(1)}
            onSubmit={handleSubmit}
          />
        )}
      </div>
    </div>
  )
}
