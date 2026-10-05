import { UserProfile, StaffSession, UserRole } from '@/types/auth'

export type AppPermission =
  | 'CREATE_OFFER'
  | 'EDIT_STORE_PROFILE'
  | 'MANAGE_STAFF_PINS'
  | 'SCAN_COUPONS'
  | 'VIEW_STORE_ANALYTICS'
  | 'CLAIM_COUPONS'
  | 'VIEW_WALLET'
  | 'MODERATE_REELS'
  | 'VERIFY_STORE_KYC'

// Canonical Role Permissions Matrix
const ROLE_PERMISSIONS: Record<UserRole, AppPermission[]> = {
  MERCHANT: [
    'CREATE_OFFER',
    'EDIT_STORE_PROFILE',
    'MANAGE_STAFF_PINS',
    'SCAN_COUPONS',
    'VIEW_STORE_ANALYTICS',
  ],
  ROLE_CASHIER: [
    'SCAN_COUPONS',
  ],
  SHOPPER: [
    'CLAIM_COUPONS',
    'VIEW_WALLET',
  ],
  SUPER_ADMIN: [
    'MODERATE_REELS',
    'VERIFY_STORE_KYC',
    'VIEW_STORE_ANALYTICS',
  ],
}

// Check if user or staff has permission
export function checkPermission(
  user: UserProfile | null,
  staff: StaffSession | null,
  permission: AppPermission
): boolean {
  if (staff) {
    return ROLE_PERMISSIONS.ROLE_CASHIER.includes(permission)
  }
  if (!user) {
    return false
  }
  const allowed = ROLE_PERMISSIONS[user.role] || []
  return allowed.includes(permission)
}

// Customer-friendly human explanation when an action is disallowed (adhering to CONTENT_GUIDELINES.md)
export function getPermissionExplanation(permission: AppPermission): string {
  switch (permission) {
    case 'CREATE_OFFER':
      return 'Only verified store owners can publish video offers.'
    case 'EDIT_STORE_PROFILE':
      return 'Only the store owner can update store address and business details.'
    case 'MANAGE_STAFF_PINS':
      return 'Only the store owner can create or change counter staff PINs.'
    case 'SCAN_COUPONS':
      return 'Only billing counter staff and store owners can scan customer coupons.'
    case 'CLAIM_COUPONS':
      return 'Store owners cannot claim their own store coupons. Sign in as a shopper.'
    case 'MODERATE_REELS':
      return 'Only platform admins can review and approve video reels.'
    case 'VIEW_STORE_ANALYTICS':
      return 'Sign in as a store owner to view detailed customer footfall.'
    default:
      return 'You do not have access to this feature. Please sign in with the required account.'
  }
}
