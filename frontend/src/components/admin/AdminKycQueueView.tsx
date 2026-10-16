import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Check, X, Eye, FileText, RefreshCw, CheckCircle2, AlertCircle, ShieldCheck } from 'lucide-react'
import { adminService, AdminKycMerchantItem } from '@/services/adminService'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Dialog } from '@/components/ui/Dialog'
import { getSafeMediaUrl } from '@/utils/safeUrl'

export const AdminKycQueueView: React.FC = () => {
  const queryClient = useQueryClient()
  const [viewingDocUrl, setViewingDocUrl] = useState<string | null>(null)
  const [rejectingMerchant, setRejectingMerchant] = useState<AdminKycMerchantItem | null>(null)
  const [rejectionReason, setRejectionReason] = useState('')
  const [reasonError, setReasonError] = useState<string | null>(null)

  const { data: queue = [], isLoading, refetch } = useQuery<AdminKycMerchantItem[]>({
    queryKey: ['admin-kyc-queue'],
    queryFn: () => adminService.listKycQueue('PENDING'),
    refetchInterval: 30000,
  })

  const decideMutation = useMutation({
    mutationFn: ({
      merchantId,
      decision,
      reason,
    }: {
      merchantId: string
      decision: 'APPROVE' | 'REJECT'
      reason?: string
    }) => adminService.decideKyc(merchantId, decision, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-kyc-queue'] })
      queryClient.invalidateQueries({ queryKey: ['admin-stats'] })
      setRejectingMerchant(null)
      setRejectionReason('')
    },
  })

  const handleApprove = (item: AdminKycMerchantItem) => {
    decideMutation.mutate({ merchantId: item.id, decision: 'APPROVE' })
  }

  const handleConfirmReject = () => {
    if (!rejectionReason.trim()) {
      setReasonError('Rejection reason is mandatory so merchant knows how to correct proof.')
      return
    }
    if (!rejectingMerchant) return
    decideMutation.mutate({
      merchantId: rejectingMerchant.id,
      decision: 'REJECT',
      reason: rejectionReason.trim(),
    })
  }

  if (isLoading) {
    return (
      <div className="py-20 text-center space-y-3 font-sans">
        <RefreshCw className="w-8 h-8 text-primary animate-spin mx-auto" />
        <p className="text-xs text-stone-500 font-medium">Scanning merchant KYC verification queue...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6 font-sans text-stone-900">
      <div className="flex items-center justify-between pb-3 border-b border-stone-200">
        <div>
          <h2 className="text-xl font-extrabold text-stone-900 tracking-tight">Merchant Verification Desk</h2>
          <p className="text-xs text-stone-500 mt-0.5">
            Audit store registration documents, tax proofs, and storefront photos.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()} className="text-xs font-bold gap-1.5">
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Queue ({queue.length})</span>
        </Button>
      </div>

      {queue.length === 0 ? (
        <div className="bg-white rounded-3xl border border-stone-200 p-12 text-center shadow-card space-y-3 max-w-md mx-auto">
          <div className="w-14 h-14 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto">
            <CheckCircle2 className="w-8 h-8" />
          </div>
          <h3 className="text-base font-extrabold text-stone-900">All Merchant KYCs Cleared!</h3>
          <p className="text-xs text-stone-500 max-w-sm mx-auto leading-relaxed">
            Zero pending store proofs in queue. Newly registered stores will show here immediately.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {queue.map((item) => (
            <div
              key={item.id}
              className="bg-white rounded-3xl border border-stone-200/80 p-5 shadow-2xs flex flex-col md:flex-row md:items-center justify-between gap-4"
            >
              <div className="space-y-1.5">
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="text-base font-black text-stone-900">{item.business_name}</h3>
                  <Badge variant="outline">{item.sector}</Badge>
                  <Badge variant="outline">{item.city}</Badge>
                  <span className="text-[10px] text-stone-400 font-mono">
                    Owner: {item.owner_phone}
                  </span>
                </div>
                <p className="text-xs text-stone-500">
                  Submitted: {new Date(item.submitted_at).toLocaleString()}
                </p>
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setViewingDocUrl(item.kyc_doc_url)}
                  className="text-xs font-bold gap-1.5"
                >
                  <Eye className="w-3.5 h-3.5 text-primary" />
                  <span>Inspect Document</span>
                </Button>
                <Button
                  variant="emerald"
                  size="sm"
                  disabled={decideMutation.isPending}
                  onClick={() => handleApprove(item)}
                  className="text-xs font-bold gap-1"
                >
                  <Check className="w-3.5 h-3.5" />
                  <span>Approve</span>
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  disabled={decideMutation.isPending}
                  onClick={() => {
                    setRejectingMerchant(item)
                    setReasonError(null)
                    setRejectionReason('')
                  }}
                  className="text-xs font-bold gap-1"
                >
                  <X className="w-3.5 h-3.5" />
                  <span>Reject</span>
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Secure Document Viewer Modal (Opens strictly as image, never inline executable) */}
      {viewingDocUrl && (
        <Dialog
          isOpen={!!viewingDocUrl}
          onClose={() => setViewingDocUrl(null)}
          title="Merchant Verification Document Proof"
          description="High-resolution image of business registration or identity proof."
          className="max-w-2xl"
        >
          <div className="py-2 flex flex-col items-center">
            <div className="max-h-[65vh] overflow-auto rounded-2xl border border-stone-200 bg-stone-50 p-2 w-full flex items-center justify-center">
              <img
                src={getSafeMediaUrl(viewingDocUrl, viewingDocUrl)}
                alt="Merchant KYC Document"
                className="max-h-[60vh] max-w-full object-contain rounded-xl"
              />
            </div>
            <div className="pt-3 w-full flex justify-end">
              <Button variant="outline" size="sm" onClick={() => setViewingDocUrl(null)}>
                Close Preview
              </Button>
            </div>
          </div>
        </Dialog>
      )}

      {/* Reject Reason Modal (Required reason) */}
      {rejectingMerchant && (
        <Dialog
          isOpen={!!rejectingMerchant}
          onClose={() => setRejectingMerchant(null)}
          title={`Reject KYC: ${rejectingMerchant.business_name}`}
          description="Provide a clear, actionable reason. This feedback will be displayed to the shopkeeper so they can upload correct proof."
        >
          <div className="space-y-4 pt-2 text-xs font-sans">
            {reasonError && (
              <div className="p-2.5 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-1.5">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{reasonError}</span>
              </div>
            )}
            <div>
              <label className="font-bold text-stone-700 block mb-1">
                Required Rejection Reason
              </label>
              <textarea
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                placeholder="e.g. Document image is blurred and registration number is unreadable. Please upload a clear photo of your Shop Act or FSSAI certificate."
                className="w-full h-24 px-3 py-2 rounded-xl border border-stone-200 text-xs focus:ring-1 focus:ring-primary"
                required
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" size="sm" onClick={() => setRejectingMerchant(null)}>
                Cancel
              </Button>
              <Button
                variant="destructive"
                size="sm"
                disabled={decideMutation.isPending}
                onClick={handleConfirmReject}
              >
                Confirm Rejection
              </Button>
            </div>
          </div>
        </Dialog>
      )}
    </div>
  )
}
