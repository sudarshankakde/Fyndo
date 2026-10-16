import React from 'react'
import { useNavigate } from 'react-router-dom'
import { QrCode } from 'lucide-react'
import { useAppSelector } from '@/store'
import { PosScannerCard } from '@/components/pos/PosScannerCard'
import { Button } from '@/components/ui/Button'

export const PosPage: React.FC = () => {
  const navigate = useNavigate()
  const staff = useAppSelector((state) => state.auth.staff)

  if (!staff) {
    return (
      <div className="bg-white rounded-3xl border border-stone-200 p-8 text-center space-y-4 max-w-md mx-auto shadow-card">
        <div className="w-14 h-14 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto">
          <QrCode className="w-7 h-7" />
        </div>
        <h2 className="text-lg font-extrabold text-stone-900">Scanner Terminal Locked</h2>
        <p className="text-xs text-stone-500">
          Enter your registered store mobile and 6-digit staff PIN to unlock the counter camera scanner.
        </p>
        <Button onClick={() => navigate('/pos/login')} variant="emerald" className="w-full">
          Sign In to Terminal
        </Button>
      </div>
    )
  }

  return <PosScannerCard staff={staff} />
}
