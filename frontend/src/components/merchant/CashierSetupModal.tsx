import React, { useState } from 'react'
import { KeyRound, ShieldCheck, AlertCircle } from 'lucide-react'
import { Dialog } from '@/components/ui/Dialog'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { merchantService, StaffCreateData } from '@/services/merchantService'

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
  const [formData, setFormData] = useState<StaffCreateData>({
    staff_name: '',
    phone: '',
    pin: '',
  })
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.staff_name.trim() || formData.phone.length !== 10 || formData.pin.length !== 6) {
      setError('Please provide staff name, 10-digit phone, and 6-digit PIN')
      return
    }

    setIsLoading(true)
    setError(null)
    try {
      await merchantService.configureStaff({
        ...formData,
        phone: `+91${formData.phone.replace(/\D/g, '')}`,
      })
      onSuccess()
      onClose()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Staff configuration failed')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title={
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-5 w-5 text-amber-400" />
          <span>Configure Store Cashier PIN</span>
        </div>
      }
      description="Setup 1 cashier terminal scanner PIN for verifying customer in-store QR codes."
      className="max-w-sm"
    >
      {error && (
        <div className="mb-4 flex items-center gap-2 p-3 rounded-xl bg-red-500/15 border border-red-500/30 text-red-400 text-xs font-semibold">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-3.5">
        <div>
          <label className="text-xs font-semibold text-slate-300 mb-1 block">Staff Name</label>
          <Input
            placeholder="e.g. Ramesh (Cashier)"
            value={formData.staff_name}
            onChange={(e) => setFormData({ ...formData, staff_name: e.target.value })}
            required
          />
        </div>

        <div>
          <label className="text-xs font-semibold text-slate-300 mb-1 block">Staff Phone</label>
          <div className="relative">
            <span className="absolute left-3 top-3 text-sm font-semibold text-slate-400">
              +91
            </span>
            <Input
              type="tel"
              placeholder="10-digit mobile"
              value={formData.phone}
              maxLength={10}
              onChange={(e) => setFormData({ ...formData, phone: e.target.value.replace(/\D/g, '') })}
              className="pl-14 text-sm font-medium"
              required
            />
          </div>
        </div>

        <div>
          <label className="text-xs font-semibold text-slate-300 mb-1 block">
            6-Digit Scanner PIN
          </label>
          <Input
            type="password"
            placeholder="••••••"
            value={formData.pin}
            maxLength={6}
            onChange={(e) => setFormData({ ...formData, pin: e.target.value.replace(/\D/g, '') })}
            className="text-center text-xl tracking-[0.4em] font-mono font-bold"
            required
          />
        </div>

        <Button type="submit" variant="gold" size="lg" className="w-full mt-2" isLoading={isLoading}>
          <KeyRound className="h-4 w-4 mr-2" />
          <span>Save Cashier Credentials</span>
        </Button>
      </form>
    </Dialog>
  )
}
