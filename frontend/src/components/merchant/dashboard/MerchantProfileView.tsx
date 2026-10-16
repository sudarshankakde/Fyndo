import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Store, ShieldCheck, MapPin, AlertCircle, FileText, UploadCloud, RefreshCw, CheckCircle2 } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { merchantService, MerchantProfileData } from '@/services/merchantService'
import { uploadAdapter } from '@/services/adapters/uploadAdapter'
import { SECTOR_DISPLAY_NAMES } from '@/config/constants'

export const MerchantProfileView: React.FC = () => {
  const queryClient = useQueryClient()
  const [resubmitGstin, setResubmitGstin] = useState('')
  const [resubmitFile, setResubmitFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [resubmitError, setResubmitError] = useState<string | null>(null)
  const [resubmitSuccess, setResubmitSuccess] = useState(false)

  const { data: profile, isLoading } = useQuery<MerchantProfileData>({
    queryKey: ['merchant-profile'],
    queryFn: () => merchantService.getProfile(),
  })

  const resubmitMutation = useMutation({
    mutationFn: (data: { kyc_doc_url: string; gstin?: string }) => merchantService.resubmitKyc(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['merchant-profile'] })
      setResubmitSuccess(true)
      setResubmitError(null)
    },
    onError: (err: any) => {
      setResubmitError(err.message || 'Failed to resubmit verification documents.')
    },
  })

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (file.size > 5 * 1024 * 1024) {
      setResubmitError('File size must be strictly under 5MB.')
      return
    }
    setResubmitFile(file)
    setResubmitError(null)
  }

  const handleResubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!resubmitFile) {
      setResubmitError('Please select a business registration document to upload.')
      return
    }

    setIsUploading(true)
    setResubmitError(null)
    try {
      const res = await uploadAdapter.upload(resubmitFile, { folder: 'kyc', resourceType: 'image' })
      resubmitMutation.mutate({
        kyc_doc_url: res.url,
        gstin: resubmitGstin.trim() || undefined,
      })
    } catch {
      setResubmitError('Failed to upload document. Please retry.')
    } finally {
      setIsUploading(false)
    }
  }

  if (isLoading) {
    return (
      <div className="py-20 text-center space-y-3 font-sans">
        <RefreshCw className="w-8 h-8 text-primary animate-spin mx-auto" />
        <p className="text-xs text-stone-500 font-medium">Loading store profile...</p>
      </div>
    )
  }

  if (!profile) {
    return <p className="text-xs text-stone-500">No profile details available.</p>
  }

  const isApproved = profile.kyc_status === 'APPROVED'
  const isPending = profile.kyc_status === 'PENDING'
  const isRejected = profile.kyc_status === 'REJECTED'

  return (
    <div className="space-y-6 max-w-2xl font-sans text-stone-900">
      <div className="flex items-center justify-between pb-3 border-b border-stone-200">
        <div>
          <h2 className="text-xl font-extrabold text-stone-900 tracking-tight">Store Profile & Verification</h2>
          <p className="text-xs text-stone-500 mt-0.5">Physical store registration details and verified coordinates.</p>
        </div>
        {isApproved && <Badge variant="success">Verified Store</Badge>}
        {isPending && <Badge variant="amber">Pending Review</Badge>}
        {isRejected && <Badge variant="destructive">Action Required</Badge>}
      </div>

      {/* KYC Rejection Notice & Resubmit Flow */}
      {isRejected && (
        <div className="bg-red-50 border border-red-200 rounded-3xl p-6 space-y-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
            <div>
              <h3 className="text-sm font-black text-red-900">Store Verification Rejected</h3>
              <p className="text-xs text-red-700 mt-1 leading-relaxed">
                <strong>Reason:</strong> {profile.kyc_rejection_reason || 'Document unreadable or invalid business proof.'}
              </p>
            </div>
          </div>

          {resubmitSuccess ? (
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-center gap-2 text-xs text-emerald-800 font-bold">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>New documents submitted successfully! Admin review usually takes ~2 hours.</span>
            </div>
          ) : (
            <form onSubmit={handleResubmit} className="space-y-3 pt-2">
              <h4 className="text-xs font-bold text-stone-800 uppercase tracking-wider">
                Resubmit Clear Verification Proof
              </h4>
              {resubmitError && <p className="text-xs text-red-600 font-medium">{resubmitError}</p>}
              <div>
                <label className="text-xs font-bold text-stone-700 block mb-1">Updated GSTIN (Optional)</label>
                <input
                  type="text"
                  value={resubmitGstin}
                  onChange={(e) => setResubmitGstin(e.target.value)}
                  placeholder="27AAAAA0000A1Z5"
                  className="w-full px-3 py-2 text-xs rounded-xl border border-stone-200 uppercase font-mono"
                />
              </div>
              <div>
                <label className="text-xs font-bold text-stone-700 block mb-1">
                  Upload Shop Certificate / FSSAI License / Electricity Bill (Max 5MB)
                </label>
                <input
                  type="file"
                  accept="image/*,application/pdf"
                  onChange={handleFileChange}
                  className="w-full text-xs text-stone-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-primary/10 file:text-primary hover:file:bg-primary/20"
                />
              </div>
              <Button
                type="submit"
                variant="primary"
                size="sm"
                disabled={isUploading || resubmitMutation.isPending}
                className="gap-2"
              >
                <UploadCloud className="w-4 h-4" />
                <span>{isUploading ? 'Uploading Document...' : 'Submit Documents for Re-review'}</span>
              </Button>
            </form>
          )}
        </div>
      )}

      {/* Profile Details Readout */}
      <div className="bg-white rounded-3xl border border-stone-200/80 p-6 shadow-2xs space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-stone-400 block">Store Name</span>
            <span className="text-sm font-black text-stone-900 mt-0.5 block">{profile.business_name}</span>
          </div>
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-stone-400 block">Sector / Category</span>
            <span className="text-sm font-bold text-stone-900 mt-0.5 block">
              {SECTOR_DISPLAY_NAMES[profile.sector]?.en || profile.sector}
            </span>
          </div>
          <div className="sm:col-span-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-stone-400 block">Physical Address</span>
            <span className="text-xs font-medium text-stone-700 mt-0.5 flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5 text-primary shrink-0" />
              <span>{profile.address_text}, {profile.city}</span>
            </span>
          </div>
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-stone-400 block">Geofence Coordinates</span>
            <span className="text-xs font-mono text-stone-600 mt-0.5 block">
              {profile.latitude.toFixed(4)}, {profile.longitude.toFixed(4)}
            </span>
          </div>
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-stone-400 block">GSTIN</span>
            <span className="text-xs font-mono text-stone-600 mt-0.5 block">
              {profile.gstin || 'Not Provided (Micro Merchant)'}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
