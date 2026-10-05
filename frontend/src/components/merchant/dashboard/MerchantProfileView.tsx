import React, { useState } from 'react'
import { Store, ShieldCheck, MapPin, Phone, CheckCircle2, FileText } from 'lucide-react'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { useFormValidation } from '@/hooks/useFormValidation'
import { storeProfileSchema } from '@/utils/validationSchemas'

interface MerchantProfileViewProps {
  onSuccess: (msg: string) => void
}

export const MerchantProfileView: React.FC<MerchantProfileViewProps> = ({ onSuccess }) => {
  const [kycUploaded, setKycUploaded] = useState(true)

  const {
    values,
    errors,
    touched,
    isSubmitting,
    setIsSubmitting,
    handleChange,
    handleBlur,
    validateAll,
  } = useFormValidation(
    {
      name: "Haldiram's Sitabuldi",
      sector: 'FOOD',
      address: 'Plot 14, Sitabuldi Main Road, Opposite Metro Station',
      city: 'Nagpur',
      phone: '9876543210',
    },
    storeProfileSchema
  )

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    const isValid = await validateAll()
    if (!isValid) return

    setIsSubmitting(true)
    setTimeout(() => {
      setIsSubmitting(false)
      onSuccess('Store profile and address details saved successfully!')
    }, 600)
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center justify-between pb-2 border-b border-stone-800">
        <div>
          <h2 className="text-xl font-bold text-stone-100 font-display">
            Store Profile & Location
          </h2>
          <p className="text-xs text-stone-400 font-mono mt-0.5">
            Physical retail location details for shopper proximity search.
          </p>
        </div>

        <Badge variant="success" className="py-1">
          <ShieldCheck className="h-3.5 w-3.5 mr-1" />
          Verified Store
        </Badge>
      </div>

      <form onSubmit={handleSave} className="space-y-4">
        {/* Store Name */}
        <div className="space-y-1">
          <label className="font-mono text-xs text-stone-300 block">Registered Store Name</label>
          <Input
            value={values.name}
            onChange={(e) => handleChange('name', e.target.value)}
            onBlur={() => handleBlur('name')}
            error={touched.name ? errors.name : undefined}
          />
        </div>

        {/* Sector & City */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1">
            <label className="font-mono text-xs text-stone-300 block">Category / Sector</label>
            <select
              value={values.sector}
              onChange={(e) => handleChange('sector', e.target.value)}
              onBlur={() => handleBlur('sector')}
              className="flex h-10 w-full rounded-lg border border-stone-800 bg-stone-900 px-3 py-2 text-sm text-stone-100 font-sans focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-amber-500/60"
            >
              <option value="FOOD">Food & Sweets</option>
              <option value="CLOTHES_FASHION">Clothes & Sarees</option>
              <option value="ELECTRONICS">Electronics & Gadgets</option>
              <option value="FOOTWEAR">Footwear & Shoes</option>
              <option value="PROPERTY">Property & Showrooms</option>
            </select>
          </div>

          <div className="space-y-1">
            <label className="font-mono text-xs text-stone-300 block">City</label>
            <select
              value={values.city}
              onChange={(e) => handleChange('city', e.target.value)}
              onBlur={() => handleBlur('city')}
              className="flex h-10 w-full rounded-lg border border-stone-800 bg-stone-900 px-3 py-2 text-sm text-stone-100 font-sans focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-amber-500/60"
            >
              <option value="Nagpur">Nagpur</option>
              <option value="Mumbai">Mumbai</option>
            </select>
          </div>
        </div>

        {/* Street Address */}
        <div className="space-y-1">
          <label className="font-mono text-xs text-stone-300 block">Physical Street Address</label>
          <Input
            value={values.address}
            onChange={(e) => handleChange('address', e.target.value)}
            onBlur={() => handleBlur('address')}
            error={touched.address ? errors.address : undefined}
          />
          <p className="text-[11px] text-stone-400 font-mono">
            Used by nearby customers for turn-by-turn directions within 2km–10km.
          </p>
        </div>

        {/* Store Contact Phone */}
        <div className="space-y-1">
          <label className="font-mono text-xs text-stone-300 block">Store Contact Number</label>
          <Input
            type="tel"
            maxLength={10}
            value={values.phone}
            onChange={(e) => handleChange('phone', e.target.value.replace(/\D/g, ''))}
            onBlur={() => handleBlur('phone')}
            error={touched.phone ? errors.phone : undefined}
          />
        </div>

        {/* KYC Document Verification Status */}
        <div className="p-4 rounded-xl border border-stone-800 bg-stone-900/40 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-stone-800 flex items-center justify-center text-amber-400">
              <FileText className="h-4 w-4" />
            </div>
            <div>
              <p className="text-xs font-bold text-stone-200">Shop Act / GST Document</p>
              <p className="text-[11px] text-stone-400">sitabuldi_haldiram_gst.pdf • Verified</p>
            </div>
          </div>
          <span className="font-mono text-[10px] text-emerald-400 px-2 py-1 rounded bg-emerald-950/60 border border-emerald-800/80">
            VERIFIED
          </span>
        </div>

        <Button type="submit" variant="primary" size="lg" className="w-full" isLoading={isSubmitting}>
          Save Store Details
        </Button>
      </form>
    </div>
  )
}
