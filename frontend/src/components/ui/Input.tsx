import React from 'react'
import { cn } from '@/utils/cn'

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: string
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = 'text', error, ...props }, ref) => {
    return (
      <div className="w-full space-y-1">
        <input
          type={type}
          ref={ref}
          className={cn(
            'flex h-10 w-full rounded-lg border border-stone-800 bg-stone-900 px-3 py-2 text-sm text-stone-100 placeholder:text-stone-500 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-amber-500/60 focus-visible:border-amber-500/80 transition-colors disabled:cursor-not-allowed disabled:opacity-40 font-sans',
            error && 'border-red-800/80 focus-visible:ring-red-500/50 text-red-200',
            className
          )}
          {...props}
        />
        {error && <p className="text-[11px] text-red-400 font-mono">{error}</p>}
      </div>
    )
  }
)

Input.displayName = 'Input'
