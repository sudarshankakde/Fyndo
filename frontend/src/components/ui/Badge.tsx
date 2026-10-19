import React from 'react'
import { cn } from '@/utils/cn'

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'success' | 'warning' | 'destructive' | 'outline' | 'amber' | 'coral'
}

export const Badge: React.FC<BadgeProps> = ({
  className,
  variant = 'default',
  children,
  ...props
}) => {
  const variants = {
    default: 'bg-stone-100 text-stone-700 border-stone-200',
    amber: 'bg-amber-50 text-amber-700 border-amber-200',
    coral: 'bg-rose-50 text-primary border-rose-200',
    success: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    warning: 'bg-yellow-50 text-yellow-800 border-yellow-200',
    destructive: 'bg-red-50 text-red-700 border-red-200',
    outline: 'border-stone-200 text-stone-600 bg-white shadow-2xs',
  }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-bold tracking-tight transition-colors font-sans',
        variants[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  )
}
