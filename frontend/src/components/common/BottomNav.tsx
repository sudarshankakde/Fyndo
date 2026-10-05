import React from 'react'
import { NavLink } from 'react-router-dom'
import { Store, QrCode, ShieldAlert, Smartphone } from 'lucide-react'
import { useTranslation } from '@/hooks/useTranslation'
import { cn } from '@/utils/cn'

export const BottomNav: React.FC = () => {
  const { t } = useTranslation()

  const navItems = [
    { to: '/merchant', icon: Store, label: t.merchant_studio },
    { to: '/pos', icon: QrCode, label: t.pos_terminal },
    { to: '/admin', icon: ShieldAlert, label: t.admin_desk },
    { to: '/app', icon: Smartphone, label: t.shopper_app },
  ]

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 bg-stone-950/95 border-t border-stone-800 px-2 py-2 sm:py-2.5">
      <div className="max-w-md mx-auto flex items-center justify-around font-mono">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                'flex flex-col items-center gap-1 px-3 py-1 rounded text-[11px] font-medium transition-colors select-none',
                isActive
                  ? 'text-amber-400 bg-stone-900 border border-stone-800'
                  : 'text-stone-400 hover:text-stone-200'
              )
            }
          >
            <item.icon className="h-4 w-4" />
            <span className="truncate max-w-[80px]">{item.label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
