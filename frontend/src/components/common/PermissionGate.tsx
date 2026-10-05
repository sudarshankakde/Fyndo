import React from 'react'
import { Lock, ShieldAlert, UserCheck } from 'lucide-react'
import { AppPermission } from '@/utils/rbac'
import { usePermissions } from '@/hooks/usePermissions'
import { Button } from '@/components/ui/Button'
import { useAppDispatch } from '@/store'
import { setAuthModalOpen } from '@/store/slices/uiSlice'

interface PermissionGateProps {
  permission: AppPermission
  children: React.ReactNode
  fallback?: React.ReactNode
  showWarning?: boolean
}

export const PermissionGate: React.FC<PermissionGateProps> = ({
  permission,
  children,
  fallback,
  showWarning = false,
}) => {
  const dispatch = useAppDispatch()
  const { can, getExplanation, role } = usePermissions()
  const hasAccess = can(permission)

  if (hasAccess) {
    return <>{children}</>
  }

  if (fallback) {
    return <>{fallback}</>
  }

  if (showWarning) {
    return (
      <div className="surface-card p-6 rounded-xl border border-stone-800 bg-stone-900/80 text-center space-y-3 max-w-md mx-auto my-6">
        <div className="h-10 w-10 rounded-lg bg-stone-800 border border-stone-700 text-amber-400 flex items-center justify-center mx-auto">
          <Lock className="h-5 w-5" />
        </div>
        <div className="space-y-1">
          <h3 className="text-sm font-bold text-stone-200 font-display">
            Action Restricted
          </h3>
          <p className="text-xs text-stone-400 leading-relaxed font-sans">
            {getExplanation(permission)}
          </p>
        </div>
        <div className="pt-2 flex justify-center gap-2">
          <Button
            variant="primary"
            size="sm"
            onClick={() => dispatch(setAuthModalOpen(true))}
            className="text-xs font-mono"
          >
            <UserCheck className="h-3.5 w-3.5 mr-1" />
            <span>Switch or Sign In</span>
          </Button>
        </div>
      </div>
    )
  }

  return null
}
