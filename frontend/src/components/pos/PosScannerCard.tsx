import React, { useState } from 'react'
import { CheckCircle2, ScanLine, AlertCircle, Sparkles } from 'lucide-react'
import confetti from 'canvas-confetti'
import { StaffSession } from '@/types/auth'
import { RedemptionVerifyResult } from '@/types/coupon'
import { redemptionService } from '@/services/redemptionService'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { useTranslation } from '@/hooks/useTranslation'

interface PosScannerCardProps {
  staff: StaffSession
}

export const PosScannerCard: React.FC<PosScannerCardProps> = ({ staff }) => {
  const { t } = useTranslation()
  const [qrPayload, setQrPayload] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [redemptionResult, setRedemptionResult] = useState<RedemptionVerifyResult | null>(null)

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!qrPayload.trim()) return

    setIsLoading(true)
    setError(null)
    setRedemptionResult(null)

    try {
      // Default to Nagpur Sitabuldi coordinates for cashier in beta
      const result = await redemptionService.verifyAndRedeem({
        qr_payload: qrPayload.trim(),
        cashier_lat: 21.1458,
        cashier_lon: 79.0882,
      })

      setRedemptionResult(result)
      setQrPayload('')

      // Celebration burst for store staff & customer!
      confetti({
        particleCount: 80,
        spread: 70,
        origin: { y: 0.6 },
        colors: ['#10B981', '#F59E0B', '#6366F1'],
      })
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Redemption verification failed')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="w-full max-w-md mx-auto rounded-3xl border border-slate-800 bg-slate-900/90 shadow-2xl p-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-2 pb-4 border-b border-slate-800 mb-5">
        <div>
          <Badge variant="amber" className="text-xs font-bold py-1 mb-1">
            POS Terminal Active
          </Badge>
          <h2 className="text-xl font-bold font-heading text-white">{staff.businessName}</h2>
          <p className="text-xs text-slate-400">Cashier: {staff.staffName}</p>
        </div>
        <div className="h-12 w-12 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center">
          <ScanLine className="h-6 w-6 animate-pulse" />
        </div>
      </div>

      {/* Success Notification */}
      {redemptionResult && (
        <div className="mb-5 p-4 rounded-2xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 animate-in fade-in zoom-in-95">
          <div className="flex items-center gap-2 font-bold text-base mb-1">
            <CheckCircle2 className="h-5 w-5 text-emerald-400" />
            <span>Discount Applied: ₹{redemptionResult.discount_applied.toFixed(2)}</span>
          </div>
          <p className="text-xs text-emerald-400 font-semibold">{redemptionResult.coupon_title}</p>
          <p className="text-[11px] text-slate-300 mt-1">
            Customer: {redemptionResult.customer_name || 'Verified Customer'}
          </p>
        </div>
      )}

      {/* Error Notification */}
      {error && (
        <div className="mb-5 flex items-center gap-2 p-3.5 rounded-xl bg-red-500/15 border border-red-500/30 text-red-400 text-xs font-semibold">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Scanner Form */}
      <form onSubmit={handleVerify} className="space-y-4">
        <div>
          <label className="text-xs font-mono text-stone-300 mb-1.5 block">
            Scan or Enter Customer Code
          </label>
          <textarea
            rows={3}
            placeholder="Scan barcode/QR code or paste customer coupon code..."
            value={qrPayload}
            onChange={(e) => setQrPayload(e.target.value)}
            className="w-full rounded-lg border border-stone-800 bg-stone-950 p-3 text-xs font-mono text-stone-200 placeholder:text-stone-600 focus:outline-none focus:ring-1 focus:ring-amber-500/80"
          />
        </div>

        <Button
          type="submit"
          variant="primary"
          size="lg"
          className="w-full"
          disabled={!qrPayload.trim() || isLoading}
          isLoading={isLoading}
        >
          <Sparkles className="h-4 w-4 mr-2" />
          <span>Apply Discount</span>
        </Button>
      </form>
    </div>
  )
}
