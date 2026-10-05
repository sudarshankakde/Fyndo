import React from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { ShieldCheck, RefreshCw, AlertCircle } from 'lucide-react'
import { Dialog } from '@/components/ui/Dialog'
import { Badge } from '@/components/ui/Badge'
import { useAppDispatch, useAppSelector } from '@/store'
import { closeQrModal } from '@/store/slices/uiSlice'
import { useDynamicQr } from '@/hooks/useDynamicQr'
import { useTranslation } from '@/hooks/useTranslation'

export const DynamicQrModal: React.FC = () => {
  const dispatch = useAppDispatch()
  const { t } = useTranslation()
  const { isQrModalOpen, activeUserCouponId } = useAppSelector((state) => state.ui)

  const { qrData, isLoading, secondsRemaining, refetch } = useDynamicQr(
    activeUserCouponId,
    isQrModalOpen
  )

  const handleClose = () => {
    dispatch(closeQrModal())
  }

  // Calculate circular SVG progress
  const progressPercent = (secondsRemaining / 60) * 100
  const circumference = 2 * Math.PI * 40
  const strokeDashoffset = circumference - (progressPercent / 100) * circumference

  return (
    <Dialog
      isOpen={isQrModalOpen}
      onClose={handleClose}
      title={
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-5 w-5 text-amber-400" />
          <span>{t.dynamic_qr_title}</span>
        </div>
      }
      description={t.qr_refresh_notice}
      className="max-w-sm text-center"
    >
      {isLoading ? (
        <div className="py-12 flex flex-col items-center justify-center gap-3">
          <RefreshCw className="h-8 w-8 text-amber-400 animate-spin" />
          <p className="text-xs text-slate-400">Generating secure one-time QR...</p>
        </div>
      ) : qrData ? (
        <div className="flex flex-col items-center gap-4 py-2">
          {/* QR Code Container */}
          <div className="p-3 bg-white rounded-xl border-2 border-stone-300 shadow-none">
            <QRCodeSVG
              value={qrData.qr_payload}
              size={180}
              level="M"
              includeMargin={false}
            />
          </div>

          {/* Countdown Ring & Seconds Counter */}
          <div className="relative flex items-center justify-center">
            <svg className="w-16 h-16 transform -rotate-90">
              <circle
                cx="32"
                cy="32"
                r="28"
                stroke="currentColor"
                strokeWidth="4"
                className="text-stone-800"
                fill="transparent"
              />
              <circle
                cx="32"
                cy="32"
                r="28"
                stroke="currentColor"
                strokeWidth="4"
                className="text-amber-500 transition-all duration-1000 ease-linear"
                fill="transparent"
                strokeDasharray={2 * Math.PI * 28}
                strokeDashoffset={
                  2 * Math.PI * 28 - (secondsRemaining / 60) * (2 * Math.PI * 28)
                }
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute flex flex-col items-center">
              <span className="font-extrabold text-base text-stone-100 font-mono leading-none">
                {secondsRemaining}s
              </span>
              <span className="text-[8px] text-stone-400 font-mono uppercase tracking-wider">
                refresh
              </span>
            </div>
          </div>

          {/* Dynamic Token & Offline Backup PIN */}
          <div className="w-full bg-stone-950 rounded-lg p-3 border border-stone-800 space-y-1 font-mono">
            <div className="flex items-center justify-between text-xs">
              <span className="text-stone-400">Security Code:</span>
              <span className="text-sm font-bold text-amber-400 tracking-wider">
                {qrData.totp_token}
              </span>
            </div>
            <div className="flex items-center justify-between text-xs pt-1 border-t border-stone-800">
              <span className="text-stone-400">{t.backup_pin}:</span>
              <span className="font-semibold text-stone-300">
                {qrData.backup_offline_pin}
              </span>
            </div>
          </div>

          <Badge variant="outline" className="text-[10px] text-stone-400 py-1">
            <AlertCircle className="h-3 w-3 mr-1 text-amber-400" />
            Live screen required at billing counter.
          </Badge>
        </div>
      ) : (
        <div className="py-6 text-center text-slate-400 text-sm">
          Failed to generate QR code.
          <button
            onClick={() => refetch()}
            className="block mx-auto mt-2 text-amber-400 font-bold underline"
          >
            Retry
          </button>
        </div>
      )}
    </Dialog>
  )
}
