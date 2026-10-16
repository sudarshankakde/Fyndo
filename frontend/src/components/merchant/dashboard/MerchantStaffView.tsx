import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { KeyRound, ShieldCheck, UserCheck, Edit, Power, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Dialog } from '@/components/ui/Dialog'
import { merchantService, StaffResponseData } from '@/services/merchantService'

const WEAK_PINS = ['0000', '1234', '1111', '2222', '3333', '4444', '5555', '6666', '7777', '8888', '9999', '000000', '123456']

export const MerchantStaffView: React.FC = () => {
  const queryClient = useQueryClient()
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [staffName, setStaffName] = useState('')
  const [phone, setPhone] = useState('')
  const [pin, setPin] = useState('')
  const [formError, setFormError] = useState<string | null>(null)

  // One-time PIN revelation modal
  const [revealedPin, setRevealedPin] = useState<string | null>(null)

  // Edit / Reset state
  const [editingStaff, setEditingStaff] = useState<StaffResponseData | null>(null)
  const [editName, setEditName] = useState('')
  const [resetPin, setResetPin] = useState('')

  // Deactivate confirmation
  const [deactivatingStaff, setDeactivatingStaff] = useState<StaffResponseData | null>(null)

  const { data: staffList = [], isLoading } = useQuery<StaffResponseData[]>({
    queryKey: ['merchant-staff'],
    queryFn: () => merchantService.listStaff(),
  })

  const createMutation = useMutation({
    mutationFn: (data: { staff_name: string; phone: string; pin: string }) =>
      merchantService.configureStaff(data),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: ['merchant-staff'] })
      setIsCreateOpen(false)
      setRevealedPin(vars.pin)
      setStaffName('')
      setPhone('')
      setPin('')
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { staff_name?: string; pin?: string; is_active?: boolean } }) =>
      merchantService.updateStaff(id, data),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: ['merchant-staff'] })
      setEditingStaff(null)
      setDeactivatingStaff(null)
      if (vars.data.pin) {
        setRevealedPin(vars.data.pin)
      }
    },
  })

  const validatePin = (p: string): boolean => {
    if (!/^\d{4,6}$/.test(p)) {
      setFormError('PIN must be 4 to 6 numeric digits.')
      return false
    }
    if (WEAK_PINS.includes(p)) {
      setFormError('PIN is too simple. Avoid common sequences like 1234 or repeating digits.')
      return false
    }
    return true
  }

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)
    if (!staffName.trim()) {
      setFormError('Staff name is required.')
      return
    }
    if (!/^[6-9]\d{9}$/.test(phone)) {
      setFormError('Enter a valid 10-digit Indian mobile number.')
      return
    }
    if (!validatePin(pin)) return
    createMutation.mutate({ staff_name: staffName.trim(), phone, pin })
  }

  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingStaff) return
    setFormError(null)
    const data: { staff_name?: string; pin?: string } = {}
    if (editName.trim() && editName.trim() !== editingStaff.staff_name) {
      data.staff_name = editName.trim()
    }
    if (resetPin) {
      if (!validatePin(resetPin)) return
      data.pin = resetPin
    }
    updateMutation.mutate({ id: editingStaff.id, data })
  }

  if (isLoading) {
    return (
      <div className="py-20 text-center space-y-3 font-sans">
        <RefreshCw className="w-8 h-8 text-primary animate-spin mx-auto" />
        <p className="text-xs text-stone-500 font-medium">Loading checkout staff accounts...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6 font-sans">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-stone-200">
        <div>
          <h2 className="text-xl font-extrabold text-stone-900 tracking-tight">Counter Staff & Cashier PINs</h2>
          <p className="text-xs text-stone-500 mt-0.5">
            Configure PINs for store cashiers to authenticate and scan customer vouchers at billing counters.
          </p>
        </div>
        <Button variant="primary" size="sm" onClick={() => setIsCreateOpen(true)} className="text-xs font-bold gap-1.5">
          <KeyRound className="h-4 w-4" />
          <span>Add Cashier Staff</span>
        </Button>
      </div>

      {staffList.length === 0 ? (
        <div className="bg-white rounded-3xl border border-stone-200 p-12 text-center shadow-card space-y-4 max-w-md mx-auto">
          <div className="w-16 h-16 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto">
            <KeyRound className="w-8 h-8" />
          </div>
          <h3 className="text-lg font-black text-stone-900">No Cashier Configured</h3>
          <p className="text-xs text-stone-500 mt-1 leading-relaxed">
            Create a cashier profile with a secure numeric PIN so your store manager can verify vouchers via the POS Scanner.
          </p>
          <Button onClick={() => setIsCreateOpen(true)} variant="primary" size="md">
            Configure Cashier PIN
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {staffList.map((staff) => (
            <div
              key={staff.id}
              className="bg-white rounded-3xl border border-stone-200/80 p-5 shadow-2xs flex flex-col justify-between space-y-4"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-stone-100 flex items-center justify-center font-black text-stone-700">
                    <UserCheck className="w-5 h-5 text-emerald-600" />
                  </div>
                  <div>
                    <h3 className="text-sm font-black text-stone-900">{staff.staff_name}</h3>
                    <p className="text-xs text-stone-400 font-mono mt-0.5">{staff.phone}</p>
                  </div>
                </div>
                <Badge variant={staff.is_active ? 'success' : 'destructive'}>
                  {staff.is_active ? 'Active Terminal' : 'Deactivated'}
                </Badge>
              </div>

              <div className="flex items-center gap-2 pt-3 border-t border-stone-100">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setEditingStaff(staff)
                    setEditName(staff.staff_name)
                    setResetPin('')
                  }}
                  className="flex-1 text-xs font-bold gap-1"
                >
                  <Edit className="w-3.5 h-3.5" />
                  Edit / Reset PIN
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setDeactivatingStaff(staff)}
                  className={`text-xs ${staff.is_active ? 'text-red-600 hover:bg-red-50' : 'text-emerald-700 hover:bg-emerald-50'}`}
                >
                  <Power className="w-3.5 h-3.5" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Show PIN Once Confirmation Modal */}
      {revealedPin && (
        <Dialog
          isOpen={!!revealedPin}
          onClose={() => setRevealedPin(null)}
          title="Cashier PIN Configured"
          description="Save this security PIN securely now. For staff privacy, it cannot be displayed again."
        >
          <div className="text-center py-4 space-y-3 font-sans">
            <div className="p-4 bg-emerald-50 rounded-2xl border border-emerald-200 inline-block mx-auto">
              <span className="font-mono text-3xl font-black text-emerald-800 tracking-widest">{revealedPin}</span>
            </div>
            <p className="text-xs text-stone-500">Provide this PIN to your counter cashier for login at /pos/login.</p>
            <Button onClick={() => setRevealedPin(null)} className="w-full">
              I Have Recorded the PIN
            </Button>
          </div>
        </Dialog>
      )}

      {/* Create Staff Modal */}
      {isCreateOpen && (
        <Dialog
          isOpen={isCreateOpen}
          onClose={() => setIsCreateOpen(false)}
          title="Add Store Cashier"
          description="Create a cashier terminal account with a secure numeric login PIN."
        >
          <form onSubmit={handleCreateSubmit} className="space-y-4 text-xs font-sans">
            {formError && (
              <div className="p-2.5 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}
            <div>
              <label className="font-bold text-stone-700 block mb-1">Staff Name / Counter Label</label>
              <input
                type="text"
                value={staffName}
                onChange={(e) => setStaffName(e.target.value)}
                placeholder="e.g. Counter 1 - Ramesh"
                className="w-full px-3 py-2 rounded-xl border border-stone-200 text-xs"
                required
              />
            </div>
            <div>
              <label className="font-bold text-stone-700 block mb-1">Mobile Number (10 digits)</label>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value.replace(/\D/g, '').slice(0, 10))}
                placeholder="e.g. 9876543210"
                className="w-full px-3 py-2 rounded-xl border border-stone-200 text-xs font-mono"
                required
              />
            </div>
            <div>
              <label className="font-bold text-stone-700 block mb-1">Terminal PIN (4-6 digits)</label>
              <input
                type="password"
                value={pin}
                onChange={(e) => setPin(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="••••••"
                className="w-full px-3 py-2 rounded-xl border border-stone-200 text-xs font-mono"
                required
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="outline" size="sm" onClick={() => setIsCreateOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" variant="primary" size="sm" disabled={createMutation.isPending}>
                Create Staff Account
              </Button>
            </div>
          </form>
        </Dialog>
      )}

      {/* Edit / Reset PIN Modal */}
      {editingStaff && (
        <Dialog
          isOpen={!!editingStaff}
          onClose={() => setEditingStaff(null)}
          title={`Edit ${editingStaff.staff_name}`}
          description="Rename cashier account or reset the terminal PIN."
        >
          <form onSubmit={handleEditSubmit} className="space-y-4 text-xs font-sans">
            {formError && (
              <div className="p-2.5 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}
            <div>
              <label className="font-bold text-stone-700 block mb-1">Staff Name</label>
              <input
                type="text"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-stone-200 text-xs"
                required
              />
            </div>
            <div>
              <label className="font-bold text-stone-700 block mb-1">New Terminal PIN (Leave blank to keep existing)</label>
              <input
                type="password"
                value={resetPin}
                onChange={(e) => setResetPin(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="••••••"
                className="w-full px-3 py-2 rounded-xl border border-stone-200 text-xs font-mono"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="outline" size="sm" onClick={() => setEditingStaff(null)}>
                Cancel
              </Button>
              <Button type="submit" variant="primary" size="sm" disabled={updateMutation.isPending}>
                Save Changes
              </Button>
            </div>
          </form>
        </Dialog>
      )}

      {/* Deactivate Confirmation Modal */}
      {deactivatingStaff && (
        <Dialog
          isOpen={!!deactivatingStaff}
          onClose={() => setDeactivatingStaff(null)}
          title="Confirm Staff Status Change"
          description={`Are you sure you want to ${deactivatingStaff.is_active ? 'deactivate' : 'reactivate'} ${deactivatingStaff.staff_name}?`}
        >
          <div className="flex justify-end gap-2 pt-4">
            <Button variant="outline" size="sm" onClick={() => setDeactivatingStaff(null)}>
              Cancel
            </Button>
            <Button
              variant={deactivatingStaff.is_active ? 'destructive' : 'primary'}
              size="sm"
              disabled={updateMutation.isPending}
              onClick={() =>
                updateMutation.mutate({
                  id: deactivatingStaff.id,
                  data: { is_active: !deactivatingStaff.is_active },
                })
              }
            >
              Confirm
            </Button>
          </div>
        </Dialog>
      )}
    </div>
  )
}
