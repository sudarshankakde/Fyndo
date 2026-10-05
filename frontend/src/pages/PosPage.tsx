import React, { useState } from 'react'
import { QrCode, KeyRound, ShieldCheck } from 'lucide-react'
import { useAppSelector } from '@/store'
import { PosScannerCard } from '@/components/pos/PosScannerCard'
import { PosLoginModal } from '@/components/pos/PosLoginModal'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { useTranslation } from '@/hooks/useTranslation'

export const PosPage: React.FC = () => {
  const { t } = useTranslation()
  const staff = useAppSelector((state) => state.auth.staff)
  const [isLoginOpen, setIsLoginOpen] = useState(false)

  return (
    <div className="min-h-screen pb-24 pt-8 max-w-lg mx-auto px-4">
      {/* Page Header */}
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-1.5">
          <Badge variant="amber">
            Billing Counter
          </Badge>
          <span className="font-mono text-xs text-stone-400">Sitabuldi Store</span>
        </div>
        <h1 className="text-2xl font-extrabold text-stone-100 font-display">{t.pos_terminal}</h1>
        <p className="text-xs text-stone-400 font-mono mt-0.5">
          Scan customer 60-second rotating security codes to apply in-store discounts.
        </p>
      </div>

      {staff ? (
        <PosScannerCard staff={staff} />
      ) : (
        <div className="surface-card rounded-xl border border-stone-800 bg-stone-900/90 p-8 text-center space-y-5 max-w-md mx-auto">
          <div className="h-14 w-14 rounded bg-stone-800 border border-stone-700 text-amber-400 flex items-center justify-center mx-auto">
            <QrCode className="h-7 w-7" />
          </div>

          <div>
            <h2 className="text-lg font-bold text-stone-100 mb-1 font-display">
              Counter Scanner Terminal
            </h2>
            <p className="text-xs text-stone-400 leading-relaxed max-w-xs mx-auto">
              Log in with your store phone number and 6-digit staff PIN to start verifying customer coupons.
            </p>
          </div>

          <div className="p-3.5 rounded-lg bg-stone-950 border border-stone-800 text-[11px] text-stone-400 text-left space-y-1 font-mono">
            <div className="flex items-center gap-1.5 text-amber-400 font-semibold">
              <ShieldCheck className="h-3.5 w-3.5" />
              <span>In-Store Verification:</span>
            </div>
            <p>
              Only real in-store scans verify coupons and ensure customers receive their authorized discount.
            </p>
          </div>

          <Button
            variant="primary"
            size="lg"
            className="w-full"
            onClick={() => setIsLoginOpen(true)}
          >
            <KeyRound className="h-4 w-4 mr-2" />
            <span>Open Counter Scanner</span>
          </Button>
        </div>
      )}

      <PosLoginModal isOpen={isLoginOpen} onClose={() => setIsLoginOpen(false)} />
    </div>
  )
}
