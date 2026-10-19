import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle2, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { LocationPicker, LocationPickerValue } from '@/components/merchant/location/LocationPicker'
import { OnboardingKycStep } from '@/components/merchant/OnboardingKycStep'
import { merchantService } from '@/services/merchantService'
import { uploadAdapter } from '@/services/adapters/uploadAdapter'
import { useAppDispatch } from '@/store'
import { updateUser } from '@/store/slices/authSlice'
import { authService } from '@/services/authService'
import { BETA_CITIES, SECTOR_DISPLAY_NAMES } from '@/config/constants'

export const MerchantOnboardingPage: React.FC = () => {
  const navigate = useNavigate()
  const dispatch = useAppDispatch()

  const [step, setStep] = useState<1 | 2 | 3 | 4>(1)
  const [businessName, setBusinessName] = useState('')
  const [sector, setSector] = useState<'FOOD' | 'FASHION' | 'FOOTWEAR' | 'ELECTRONICS' | 'REAL_ESTATE'>('FOOD')
  const [gstin, setGstin] = useState('')
  const [addressText, setAddressText] = useState('')

  const [location, setLocation] = useState<LocationPickerValue>({
    latitude: BETA_CITIES.NAGPUR.center.lat,
    longitude: BETA_CITIES.NAGPUR.center.lon,
    city: 'Nagpur',
    address: 'Sitabuldi Market, Nagpur',
    source: 'map',
    isEntranceConfirmed: false,
  })

  const [kycFile, setKycFile] = useState<File | null>(null)
  const [kycDocUrl, setKycDocUrl] = useState('')
  const [isUploadingKyc, setIsUploadingKyc] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isSubmitted, setIsSubmitted] = useState(false)

  // Draft saving in sessionStorage
  useEffect(() => {
    const draft = sessionStorage.getItem('fyndo_onboard_draft')
    if (draft) {
      try {
        const parsed = JSON.parse(draft)
        if (parsed.businessName) setBusinessName(parsed.businessName)
        if (parsed.sector) setSector(parsed.sector)
        if (parsed.gstin) setGstin(parsed.gstin)
        if (parsed.addressText) setAddressText(parsed.addressText)
      } catch {
        // Ignore corrupted draft
      }
    }
  }, [])

  const saveDraft = () => {
    sessionStorage.setItem(
      'fyndo_onboard_draft',
      JSON.stringify({ businessName, sector, gstin, addressText })
    )
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (file.size > 5 * 1024 * 1024) {
      setErrorMessage('Document size must be under 5MB.')
      return
    }

    setKycFile(file)
    setIsUploadingKyc(true)
    setErrorMessage(null)

    try {
      const res = await uploadAdapter.upload(file, { folder: 'kyc', resourceType: 'image' })
      setKycDocUrl(res.url)
    } catch {
      setKycDocUrl('')
      setErrorMessage('Document upload failed. Please try uploading your verification document again.')
    } finally {
      setIsUploadingKyc(false)
    }
  }

  const handleSubmit = async () => {
    if (!kycDocUrl) {
      setErrorMessage('Please upload a valid business document before submitting.')
      return
    }

    setIsSubmitting(true)
    setErrorMessage(null)

    try {
      await merchantService.onboardStore({
        business_name: businessName.trim(),
        sector,
        address_text: addressText.trim() || location.address,
        city: location.city,
        latitude: location.latitude,
        longitude: location.longitude,
        gstin: gstin.trim() || undefined,
        kyc_doc_url: kycDocUrl,
      })

      // Re-fetch /auth/me so user role updates to MERCHANT
      try {
        const freshUser = await authService.getMe()
        dispatch(updateUser(freshUser))
      } catch {
        dispatch(updateUser({ role: 'MERCHANT', business_name: businessName.trim() }))
      }

      sessionStorage.removeItem('fyndo_onboard_draft')
      setIsSubmitted(true)
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to submit store onboarding. Please check details.')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (isSubmitted) {
    return (
      <div className="min-h-screen bg-[#FAFAFA] flex items-center justify-center p-4 font-sans text-stone-900">
        <div className="max-w-md w-full bg-white rounded-3xl border border-stone-200 p-8 shadow-card text-center space-y-4">
          <div className="w-16 h-16 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto">
            <CheckCircle2 className="w-9 h-9" />
          </div>
          <h1 className="text-xl font-extrabold text-stone-900">Store Profile Submitted!</h1>
          <p className="text-xs text-stone-500 leading-relaxed">
            We review store verification documents within 2 hours to keep the platform trustworthy for local customers.
          </p>
          <div className="pt-2">
            <Button onClick={() => navigate('/merchant')} className="w-full">
              Open Store Manager
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#FAFAFA] text-stone-900 p-4 sm:p-6 lg:p-10 font-sans">
      <div className="max-w-xl w-full mx-auto space-y-6">
        <div className="space-y-2">
          <span className="text-xs font-bold text-primary tracking-wide uppercase">Step {step} of 4</span>
          <h1 className="text-2xl font-extrabold text-stone-900 tracking-tight">Register Your Shop</h1>
          <div className="h-1.5 w-full bg-stone-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-primary transition-all duration-300"
              style={{ width: `${(step / 4) * 100}%` }}
            />
          </div>
        </div>

        {errorMessage && (
          <div className="p-3.5 rounded-2xl bg-red-50 border border-red-200 text-red-700 text-xs font-medium flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
            <span>{errorMessage}</span>
          </div>
        )}

        <div className="bg-white rounded-3xl border border-stone-200 p-6 sm:p-8 shadow-card space-y-6">
          {step === 1 && (
            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-stone-700 block">Store / Business Name</label>
                <input
                  type="text"
                  value={businessName}
                  onChange={(e) => setBusinessName(e.target.value)}
                  placeholder="e.g. Haldiram Sweets, Modern Footwear"
                  className="h-11 w-full rounded-xl border border-stone-200 bg-white px-3.5 text-sm font-semibold text-stone-900 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary shadow-2xs"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-stone-700 block">Business Category</label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {(Object.keys(SECTOR_DISPLAY_NAMES) as Array<keyof typeof SECTOR_DISPLAY_NAMES>).map((sec) => (
                    <button
                      key={sec}
                      type="button"
                      onClick={() => setSector(sec as any)}
                      className={`p-3 rounded-xl border text-left transition-all ${
                        sector === sec
                          ? 'border-primary bg-primary/5 text-primary font-bold shadow-xs'
                          : 'border-stone-200 bg-white text-stone-700 hover:bg-stone-50'
                      }`}
                    >
                      <p className="text-xs font-bold">{SECTOR_DISPLAY_NAMES[sec].en}</p>
                      <p className="text-[10px] text-stone-400 mt-0.5">{SECTOR_DISPLAY_NAMES[sec].hi}</p>
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-stone-700 block">
                  GSTIN <span className="text-stone-400 font-normal">(Optional)</span>
                </label>
                <input
                  type="text"
                  value={gstin}
                  onChange={(e) => setGstin(e.target.value.toUpperCase())}
                  placeholder="e.g. 27AAAAA0000A1Z5"
                  className="h-11 w-full rounded-xl border border-stone-200 bg-white px-3.5 text-xs font-mono font-semibold text-stone-900 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary shadow-2xs uppercase"
                />
              </div>

              <Button
                disabled={businessName.trim().length < 2}
                onClick={() => {
                  saveDraft()
                  setStep(2)
                }}
                className="w-full mt-4"
              >
                Next: Shop Location
              </Button>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <LocationPicker value={location} onChange={setLocation} />

              <div className="space-y-1.5 pt-2">
                <label className="text-xs font-bold text-stone-700 block">Complete Shop Address</label>
                <input
                  type="text"
                  value={addressText}
                  onChange={(e) => setAddressText(e.target.value)}
                  placeholder="Shop No., Street, Market Name"
                  className="h-11 w-full rounded-xl border border-stone-200 bg-white px-3.5 text-sm font-semibold text-stone-900 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary shadow-2xs"
                />
              </div>

              <div className="flex gap-2 pt-2">
                <Button variant="outline" onClick={() => setStep(1)} className="flex-1">
                  Back
                </Button>
                <Button
                  disabled={!location.isEntranceConfirmed || (addressText.trim().length < 5 && location.address.length < 5)}
                  onClick={() => {
                    saveDraft()
                    setStep(3)
                  }}
                  className="flex-1"
                >
                  Next: KYC Document
                </Button>
              </div>
            </div>
          )}

          {(step === 3 || step === 4) && (
            <OnboardingKycStep
              step={step}
              kycFile={kycFile}
              isUploadingKyc={isUploadingKyc}
              onFileUpload={handleFileUpload}
              onBack={() => setStep(step === 3 ? 2 : 3)}
              onNext={() => setStep(4)}
              onSubmit={handleSubmit}
              isSubmitting={isSubmitting}
              businessName={businessName}
              sector={sector}
              location={location}
              addressText={addressText}
            />
          )}
        </div>
      </div>
    </div>
  )
}
