import React, { useEffect, useRef } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { ShieldCheck, RefreshCw, AlertCircle, Copy, Check } from 'lucide-react'
import confetti from 'canvas-confetti'
import { Dialog } from '@/components/ui/Dialog'
import { useAppDispatch, useAppSelector } from '@/store'
import { closeQrModal } from '@/store/slices/uiSlice'
import { useDynamicQr } from '@/hooks/useDynamicQr'
import { couponService } from '@/services/couponService'

export const DynamicQrModal: React.FC = () => {
  const dispatch = useAppDispatch()
  const { isQrModalOpen, activeUserCouponId } = useAppSelector((state) => state.ui)
  const wakeLockRef = useRef<any>(null)
  const [copied, setCopied] = React.useState(false)

  const { qrData, isLoading, isError, secondsRemaining, refetch } = useDynamicQr(
    activeUserCouponId,
    isQrModalOpen
  )

  // Wake Lock API integration to keep screen on while presenting QR at counter
  useEffect(() => {
    if (isQrModalOpen && 'wakeLock' in navigator) {
      navigator.wakeLock.request('screen').then((lock) => {
        wakeLockRef.current = lock
      }).catch(() => {})
    }
    return () => {
      if (wakeLockRef.current) {
        wakeLockRef.current.release().catch(() => {})
        wakeLockRef.current = null
      }
    }
  }, [isQrModalOpen])

  // Poll wallet every 5s to detect in-store redemption completion automatically (paused when hidden)
  useEffect(() => {
    if (!isQrModalOpen || !activeUserCouponId) return

    const interval = setInterval(async () => {
      if (document.visibilityState === 'hidden') return
      try {
        const coupons = await couponService.getUserWallet()
        const current = coupons.find((c) => c.id === activeUserCouponId)
        if (current && current.status === 'REDEEMED') {
          dispatch(closeQrModal())
          confetti({
            particleCount: 80,
            spread: 70,
            origin: { y: 0.6 },
            colors: ['#FF385C', '#10B981', '#F59E0B'],
          })
        }
      } catch {
        // Ignore polling errors
      }
    }, 5000)

    return () => clearInterval(interval)
  }, [isQrModalOpen, activeUserCouponId, dispatch])

  const handleCopyCode = () => {
    const code = activeUserCouponId?.slice(0, 8).toUpperCase() || ''
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const codeDisplay = activeUserCouponId?.slice(0, 8).toUpperCase()

  return (
    <Dialog
      isOpen={isQrModalOpen}
      onClose={() => dispatch(closeQrModal())}
      title={
        <div className="flex items-center gap-2 text-stone-900 font-extrabold text-base">
          <ShieldCheck className="h-5 w-5 text-emerald-600" />
          <span>Present Pass at Checkout</span>
        </div>
      }
      description="Present this dynamic security QR to the cashier before final bill settlement."
      className="max-w-sm text-center bg-white border border-stone-200 shadow-modal rounded-3xl"
    >
      {isLoading ? (
        <div className="py-12 flex flex-col items-center justify-center gap-3">
          <RefreshCw className="h-8 w-8 text-primary animate-spin" />
          <p className="text-xs text-stone-500 font-medium">Generating fresh security code...</p>
        </div>
      ) : isError ? (
        <div className="py-8 text-center space-y-3 font-sans">
          <AlertCircle className="w-10 h-10 text-amber-500 mx-auto" />
          <h4 className="text-sm font-black text-stone-900">Pass Expired or Redeemed</h4>
          <p className="text-xs text-stone-500">
            This voucher code is no longer active. Check your wallet for updated passes.
          </p>
          <button
            onClick={() => refetch()}
            className="px-4 py-1.5 rounded-full bg-stone-100 hover:bg-stone-200 text-stone-800 text-xs font-bold"
          >
            Retry Refresh
          </button>
        </div>
      ) : qrData ? (
        <div className="flex flex-col items-center gap-4 py-2 font-sans">
          {/* High-Contrast QR Code Pad (Stitch Screen 4) */}
          <div className="p-4 bg-white rounded-2xl border-2 border-stone-200 shadow-2xs">
            <QRCodeSVG
              value={qrData.qr_payload}
              size={180}
              level="M"
              includeMargin={false}
            />
          </div>

          {/* 60s Circular Countdown Ring */}
          <div className="relative flex items-center justify-center">
            <svg className="w-14 h-14 transform -rotate-90">
              <circle
                cx="28"
                cy="28"
                r="24"
                stroke="currentColor"
                strokeWidth="3.5"
                className="text-stone-100"
                fill="transparent"
              />
              <circle
                cx="28"
                cy="28"
                r="24"
                stroke="currentColor"
                strokeWidth="3.5"
                className="text-primary transition-all duration-1000 ease-linear"
                fill="transparent"
                strokeDasharray={2 * Math.PI * 24}
                strokeDashoffset={
                  2 * Math.PI * 24 - (secondsRemaining / 60) * (2 * Math.PI * 24)
                }
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute flex flex-col items-center">
              <span className="font-extrabold text-sm text-stone-900 font-mono leading-none">
                {secondsRemaining}s
              </span>
              <span className="text-[7px] text-stone-400 font-mono uppercase tracking-wider">
                refresh
              </span>
            </div>
          </div>

          {/* Anti-screenshot notice (Stitch Screen 4 Spec) */}
          <p className="text-[11px] text-stone-500 max-w-xs leading-relaxed">
            Screenshots are not accepted at counter. Code refreshes every 60 seconds.
          </p>

          {/* Alphanumeric Pass Code with Copy & Backup PIN */}
          <div className="w-full bg-stone-50 rounded-2xl p-3 border border-stone-200 text-xs font-mono space-y-2">
            <div className="flex justify-between items-center">
              <div className="flex flex-col text-left">
                <span className="text-[10px] text-stone-400 font-sans uppercase">Pass Code:</span>
                <span className="font-extrabold text-stone-900 font-mono text-sm tracking-wider">
                  FYNDO-{codeDisplay}
                </span>
              </div>
              <button
                type="button"
                onClick={handleCopyCode}
                className="px-2.5 py-1 rounded-lg bg-white border border-stone-200 text-[11px] font-bold text-stone-700 hover:bg-stone-100 flex items-center gap-1 font-sans"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>
            </div>

            {qrData.backup_offline_pin && (
              <div className="flex justify-between items-center pt-2 border-t border-stone-200">
                <span className="text-stone-500 font-sans text-[11px]">Cashier Backup PIN:</span>
                <span className="font-extrabold text-emerald-700 tracking-widest text-sm">
                  {qrData.backup_offline_pin}
                </span>
              </div>
            )}
          </div>
        </div>
      ) : null}
    </Dialog>
  )
}
