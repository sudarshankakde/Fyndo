import React from 'react'
import { UploadCloud } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { SECTOR_DISPLAY_NAMES } from '@/config/constants'
import { LocationPickerValue } from '@/components/merchant/location/LocationPicker'

interface OnboardingKycStepProps {
  step: 3 | 4
  kycFile: File | null
  isUploadingKyc: boolean
  onFileUpload: (e: React.ChangeEvent<HTMLInputElement>) => void
  onBack: () => void
  onNext: () => void
  onSubmit: () => void
  isSubmitting: boolean
  businessName: string
  sector: 'FOOD' | 'FASHION' | 'FOOTWEAR' | 'ELECTRONICS' | 'REAL_ESTATE'
  location: LocationPickerValue
  addressText: string
}

export const OnboardingKycStep: React.FC<OnboardingKycStepProps> = ({
  step,
  kycFile,
  isUploadingKyc,
  onFileUpload,
  onBack,
  onNext,
  onSubmit,
  isSubmitting,
  businessName,
  sector,
  location,
  addressText,
}) => {
  if (step === 3) {
    return (
      <div className="space-y-4 font-sans">
        <div>
          <h2 className="text-sm font-extrabold text-stone-900">Upload Shop Proof</h2>
          <p className="text-xs text-stone-500 mt-0.5">
            Attach your GST Certificate, Gumasta license, or Shop registration document (PDF/JPG up to 5MB).
          </p>
        </div>

        <label className="border-2 border-dashed border-stone-200 hover:border-primary rounded-2xl p-6 flex flex-col items-center justify-center cursor-pointer transition-all bg-stone-50/50 hover:bg-stone-50">
          <UploadCloud className="w-8 h-8 text-stone-400 mb-2" />
          <span className="text-xs font-bold text-stone-800">
            {kycFile ? kycFile.name : 'Click to select shop document'}
          </span>
          <span className="text-[10px] text-stone-400 mt-1">PDF, JPG, or PNG up to 5MB</span>
          <input
            type="file"
            accept="application/pdf,image/jpeg,image/png"
            onChange={onFileUpload}
            className="hidden"
          />
        </label>

        {isUploadingKyc && (
          <p className="text-xs text-primary font-bold text-center">
            Uploading verification document...
          </p>
        )}

        <div className="flex gap-2 pt-2">
          <Button variant="outline" onClick={onBack} className="flex-1">
            Back
          </Button>
          <Button onClick={onNext} className="flex-1">
            Next: Review & Submit
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4 font-sans">
      <h2 className="text-sm font-extrabold text-stone-900">Review Store Details</h2>
      <div className="bg-stone-50 rounded-2xl p-4 border border-stone-200 space-y-2 text-xs">
        <div className="flex justify-between">
          <span className="text-stone-500">Business Name:</span>
          <span className="font-bold text-stone-900">{businessName}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-stone-500">Category:</span>
          <span className="font-bold text-stone-900">{SECTOR_DISPLAY_NAMES[sector]?.en}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-stone-500">City:</span>
          <span className="font-bold text-stone-900">{location.city}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-stone-500">Address:</span>
          <span className="font-bold text-stone-900 text-right truncate max-w-[200px]">
            {addressText || location.address}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-stone-500">Entrance Pin:</span>
          <span className="font-mono text-stone-900">
            {location.latitude.toFixed(4)}, {location.longitude.toFixed(4)}
          </span>
        </div>
      </div>

      <div className="flex gap-2 pt-2">
        <Button variant="outline" onClick={onBack} className="flex-1">
          Back
        </Button>
        <Button isLoading={isSubmitting} onClick={onSubmit} className="flex-1">
          Submit For Verification
        </Button>
      </div>
    </div>
  )
}
