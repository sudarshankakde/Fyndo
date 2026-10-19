import React, { useState } from 'react'
import { QrCode } from 'lucide-react'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { useAppDispatch } from '@/store'
import { setStaffSession } from '@/store/slices/authSlice'
import { authService } from '@/services/authService'
import { phoneLoginSchema } from '@/utils/validationSchemas'

interface CashierPinLoginFormProps {
  onServerError: (error: string | null) => void
}

export const CashierPinLoginForm: React.FC<CashierPinLoginFormProps> = ({ onServerError }) => {
  const dispatch = useAppDispatch()
  const [cashierStorePhone, setCashierStorePhone] = useState('')
  const [cashierPhoneError, setCashierPhoneError] = useState<string | null>(null)
  const [cashierPin, setCashierPin] = useState('')
  const [cashierPinError, setCashierPinError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const handleCashierPhoneBlur = async () => {
    try {
      await phoneLoginSchema.validate({ phone: cashierStorePhone })
      setCashierPhoneError(null)
    } catch (err: any) {
      setCashierPhoneError(err.message)
    }
  }

  const handleCashierPinBlur = async () => {
    if (cashierPin.length !== 6) {
      setCashierPinError('Enter the complete 6-digit staff PIN')
    } else {
      setCashierPinError(null)
    }
  }

  const handleCashierLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    onServerError(null)

    if (cashierStorePhone.length !== 10 || cashierPin.length !== 6) {
      onServerError('Please enter a valid 10-digit phone and 6-digit PIN')
      return
    }

    setIsLoading(true)
    try {
      const fullPhone = `+91${cashierStorePhone.trim()}`
      const session = await authService.staffLogin(fullPhone, cashierPin)
      dispatch(setStaffSession(session))
    } catch (err: any) {
      onServerError(err.message || 'Invalid store phone or cashier PIN')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <form onSubmit={handleCashierLogin} className="space-y-4">
      <div className="space-y-1">
        <label className="font-mono text-xs text-stone-300 block">Store Owner Phone</label>
        <div className="relative">
          <span className="absolute left-3 top-2.5 text-xs font-mono font-bold text-stone-400 select-none">
            +91
          </span>
          <Input
            type="tel"
            placeholder="10-digit registered phone"
            value={cashierStorePhone}
            maxLength={10}
            onChange={(e) => {
              setCashierStorePhone(e.target.value.replace(/\D/g, ''))
              if (cashierPhoneError) setCashierPhoneError(null)
            }}
            onBlur={handleCashierPhoneBlur}
            error={cashierPhoneError || undefined}
            className="pl-12 text-sm font-mono tracking-wider"
          />
        </div>
      </div>

      <div className="space-y-1">
        <label className="font-mono text-xs text-stone-300 block">6-Digit Counter PIN</label>
        <Input
          type="password"
          placeholder="••••••"
          value={cashierPin}
          maxLength={6}
          onChange={(e) => {
            setCashierPin(e.target.value.replace(/\D/g, ''))
            if (cashierPinError) setCashierPinError(null)
          }}
          onBlur={handleCashierPinBlur}
          error={cashierPinError || undefined}
          className="text-center text-xl tracking-[0.4em] font-mono font-bold"
        />
      </div>

      <Button type="submit" variant="primary" size="md" className="w-full" isLoading={isLoading}>
        <QrCode className="h-4 w-4 mr-2" />
        <span>Open Counter Scanner</span>
      </Button>
    </form>
  )
}
