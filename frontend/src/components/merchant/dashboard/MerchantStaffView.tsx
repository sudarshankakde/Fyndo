import React, { useState } from 'react'
import { KeyRound, UserCheck, Plus, Trash2, ShieldCheck, CheckCircle2 } from 'lucide-react'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { useFormValidation } from '@/hooks/useFormValidation'
import { cashierPinSchema } from '@/utils/validationSchemas'

interface StaffItem {
  id: string
  name: string
  pin: string
  createdAt: string
  active: boolean
}

const INITIAL_STAFF: StaffItem[] = [
  {
    id: 'STF-01',
    name: 'Rajesh Sharma (Counter 1)',
    pin: '123456',
    createdAt: 'Active today',
    active: true,
  },
  {
    id: 'STF-02',
    name: 'Pooja Patil (Billing 2)',
    pin: '654321',
    createdAt: 'Active today',
    active: true,
  },
]

interface MerchantStaffViewProps {
  onSuccess: (msg: string) => void
}

export const MerchantStaffView: React.FC<MerchantStaffViewProps> = ({ onSuccess }) => {
  const [staffList, setStaffList] = useState<StaffItem[]>(INITIAL_STAFF)
  const [isAdding, setIsAdding] = useState(false)

  const {
    values,
    errors,
    touched,
    isSubmitting,
    setIsSubmitting,
    handleChange,
    handleBlur,
    validateAll,
    resetForm,
  } = useFormValidation(
    {
      staffName: '',
      pin: '',
    },
    cashierPinSchema
  )

  const handleAddStaff = async (e: React.FormEvent) => {
    e.preventDefault()
    const isValid = await validateAll()
    if (!isValid) return

    setIsSubmitting(true)
    setTimeout(() => {
      const newStaff: StaffItem = {
        id: `STF-0${staffList.length + 1}`,
        name: values.staffName,
        pin: values.pin,
        createdAt: 'Just now',
        active: true,
      }
      setStaffList((prev) => [newStaff, ...prev])
      setIsSubmitting(false)
      setIsAdding(false)
      resetForm()
      onSuccess(`Counter PIN created for ${values.staffName}!`)
    }, 500)
  }

  const handleDeleteStaff = (id: string) => {
    setStaffList((prev) => prev.filter((s) => s.id !== id))
    onSuccess('Staff counter access removed.')
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-stone-800">
        <div>
          <h2 className="text-xl font-bold text-stone-100 font-display">
            Counter Staff & Scanner PINs
          </h2>
          <p className="text-xs text-stone-400 font-mono mt-0.5">
            Create 6-digit PINs for store staff to redeem coupons at checkout.
          </p>
        </div>

        {!isAdding && (
          <Button variant="primary" size="sm" onClick={() => setIsAdding(true)} className="text-xs">
            <Plus className="h-3.5 w-3.5 mr-1" />
            <span>Add Cashier Staff</span>
          </Button>
        )}
      </div>

      {/* Add Staff Form with onBlur Yup validation */}
      {isAdding && (
        <form
          onSubmit={handleAddStaff}
          className="surface-card p-5 rounded-xl border border-stone-800 bg-stone-900/90 space-y-4 animate-in fade-in"
        >
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-sm text-stone-100 font-display">New Cashier PIN</h3>
            <button
              type="button"
              onClick={() => {
                setIsAdding(false)
                resetForm()
              }}
              className="text-stone-500 hover:text-stone-300 text-xs font-mono"
            >
              Cancel
            </button>
          </div>

          <div className="space-y-1">
            <label className="font-mono text-xs text-stone-300 block">Staff Name / Counter</label>
            <Input
              placeholder="e.g. Ramesh Kulkarni (Billing 1)"
              value={values.staffName}
              onChange={(e) => handleChange('staffName', e.target.value)}
              onBlur={() => handleBlur('staffName')}
              error={touched.staffName ? errors.staffName : undefined}
            />
          </div>

          <div className="space-y-1">
            <label className="font-mono text-xs text-stone-300 block">6-Digit Counter PIN</label>
            <Input
              type="password"
              maxLength={6}
              placeholder="••••••"
              value={values.pin}
              onChange={(e) => handleChange('pin', e.target.value.replace(/\D/g, ''))}
              onBlur={() => handleBlur('pin')}
              error={touched.pin ? errors.pin : undefined}
              className="font-mono tracking-widest text-center text-lg"
            />
            <p className="text-[11px] text-stone-500 font-mono">
              The cashier enters this PIN on the counter scanner terminal.
            </p>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => {
                setIsAdding(false)
                resetForm()
              }}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="sm" isLoading={isSubmitting}>
              Save Counter PIN
            </Button>
          </div>
        </form>
      )}

      {/* Staff List */}
      <div className="space-y-3">
        {staffList.map((stf) => (
          <div
            key={stf.id}
            className="surface-card p-4 rounded-xl border border-stone-800 bg-stone-900/60 flex items-center justify-between gap-4"
          >
            <div className="flex items-center gap-3">
              <div className="h-9 w-9 rounded-lg bg-stone-800 flex items-center justify-center text-amber-400 font-mono font-bold text-xs">
                {stf.id.slice(-2)}
              </div>
              <div>
                <h4 className="font-bold text-sm text-stone-200">{stf.name}</h4>
                <div className="flex items-center gap-2 text-[11px] font-mono text-stone-400 mt-0.5">
                  <span>PIN: ••••••</span>
                  <span>•</span>
                  <span>{stf.createdAt}</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Badge variant="success" className="text-[9px]">
                Active
              </Badge>
              <button
                onClick={() => handleDeleteStaff(stf.id)}
                className="p-1.5 rounded hover:bg-stone-800 text-stone-500 hover:text-red-400 transition-colors"
                title="Remove staff"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
