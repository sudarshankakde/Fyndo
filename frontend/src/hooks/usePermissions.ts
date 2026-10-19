import { useAppSelector } from '@/store'
import { AppPermission, checkPermission, getPermissionExplanation } from '@/utils/rbac'
import { UserRole } from '@/types/auth'

export function usePermissions() {
  const { user, staff, isAuthenticated } = useAppSelector((state) => state.auth)

  const role: UserRole | 'ANONYMOUS' = staff
    ? 'ROLE_CASHIER'
    : user
    ? user.role
    : 'ANONYMOUS'

  const can = (permission: AppPermission): boolean => {
    return checkPermission(user, staff, permission)
  }

  const getExplanation = (permission: AppPermission): string => {
    return getPermissionExplanation(permission)
  }

  return {
    role,
    isAuthenticated,
    user,
    staff,
    can,
    getExplanation,
    isMerchant: role === 'MERCHANT',
    isStaff: role === 'ROLE_CASHIER',
    isShopper: role === 'SHOPPER',
    isAdmin: role === 'SUPER_ADMIN',
  }
}
