import React from 'react'
import { cn } from '@/utils/cn'

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'success' | 'warning' | 'destructive' | 'outline' | 'amber'
}

export const Badge: React.FC<BadgeProps> = ({
  className,
  variant = 'default',
  children,
  ...props
}) => {
  const variants = {
    default: 'bg-stone-900 text-stone-300 border-stone-800',
    amber: 'bg-amber-950/40 text-amber-400 border-amber-800/60',
    success: 'bg-emerald-950/40 text-emerald-400 border-emerald-800/60',
    warning: 'bg-yellow-950/40 text-yellow-400 border-yellow-800/60',
    destructive: 'bg-red-950/40 text-red-400 border-red-800/60',
    outline: 'border-stone-800 text-stone-400 bg-transparent',
  }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded border px-2 py-0.5 font-mono text-[10px] font-medium tracking-wide uppercase transition-colors',
        variants[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  )
}
