import React, { useState } from 'react'
import { KeyRound, AlertCircle, CheckCircle2 } from 'lucide-react'
import { Dialog } from '@/components/ui/Dialog'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { merchantService, StaffCreateData } from '@/services/merchantService'
import { useAppSelector } from '@/store'

interface CashierSetupModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export const CashierSetupModal: React.FC<CashierSetupModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { user } = useAppSelector((state) => state.auth)
  const [formData, setFormData] = useState<StaffCreateData>({
    staff_name: '',
    phone: '',
    pin: '',
  })
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [justSavedPin, setJustSavedPin] = useState<string | null>(null)

  const validatePin = (pin: string): string | null => {
    if (pin.length !== 6) return 'PIN must be exactly 6 digits.'
    if (pin === '123456' || pin === '654321' || pin === '000000') {
      return 'Please choose a stronger PIN (avoid 123456 or 000000).'
    }
    if (/^(\d)\1{5}$/.test(pin)) {
      return 'Repeated digits (like 111111) are not allowed.'
    }
    return null
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.staff_name.trim() || formData.phone.length !== 10) {
      setError('Please provide staff name and a 10-digit mobile number.')
      return
    }

    const pinErr = validatePin(formData.pin)
    if (pinErr) {
      setError(pinErr)
      return
    }

    setIsLoading(true)
    setError(null)
    try {
      await merchantService.configureStaff({
        staff_name: formData.staff_name.trim(),
        phone: `+91${formData.phone.replace(/\D/g, '')}`,
        pin: formData.pin,
      })
      setJustSavedPin(formData.pin)
      onSuccess()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Staff configuration failed')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Dialog
      isOpen={isOpen}
      onClose={() => {
        setJustSavedPin(null)
        onClose()
      }}
      title={
        <div className="flex items-center gap-2 text-stone-900 font-extrabold text-base">
          <KeyRound className="h-5 w-5 text-emerald-600" />
          <span>Create Counter Scanner PIN</span>
        </div>
      }
      description="Configure one counter terminal PIN for your cashier to scan customer discount codes."
      className="max-w-md bg-white border border-stone-200 shadow-modal rounded-3xl"
    >
      {justSavedPin ? (
        <div className="text-center py-3 space-y-4 font-sans">
          <div className="w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto">
            <CheckCircle2 className="w-7 h-7" />
          </div>
          <div>
            <h3 className="text-sm font-extrabold text-stone-900">Counter PIN Configured!</h3>
            <p className="text-xs text-stone-500 mt-1">
              Give this 6-digit PIN to your cashier. They will log in using your store phone ({user?.phone || 'registered store mobile'}).
            </p>
          </div>
          <div className="bg-stone-50 border border-stone-200 rounded-2xl p-4 font-mono text-2xl font-extrabold text-stone-900 tracking-[0.4em]">
            {justSavedPin}
          </div>
          <Button
            onClick={() => {
              setJustSavedPin(null)
              onClose()
            }}
            className="w-full"
          >
            Done
          </Button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4 font-sans">
          {error && (
            <div className="flex items-center gap-2 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs font-semibold">
              <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="text-xs font-bold text-stone-700 mb-1 block">Cashier / Staff Name</label>
            <Input
              placeholder="e.g. Ramesh (Billing Counter)"
              value={formData.staff_name}
              onChange={(e) => setFormData({ ...formData, staff_name: e.target.value })}
              required
            />
          </div>

          <div>
            <label className="text-xs font-bold text-stone-700 mb-1 block">Staff Mobile Number</label>
            <div className="relative flex items-center">
              <span className="absolute left-3 text-xs font-bold text-stone-400 select-none">+91</span>
              <Input
                type="tel"
                placeholder="10-digit mobile"
                value={formData.phone}
                maxLength={10}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value.replace(/\D/g, '') })}
                className="pl-11"
                required
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-bold text-stone-700 mb-1 block">6-Digit PIN (for Scanner Login)</label>
            <Input
              type="password"
              placeholder="••••••"
              value={formData.pin}
              maxLength={6}
              onChange={(e) => setFormData({ ...formData, pin: e.target.value.replace(/\D/g, '') })}
              className="text-center text-lg tracking-[0.4em] font-mono font-bold"
              required
            />
          </div>

          <Button type="submit" variant="emerald" className="w-full mt-2" isLoading={isLoading}>
            Save Counter PIN
          </Button>
        </form>
      )}
    </Dialog>
  )
}
