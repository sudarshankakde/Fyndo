import React from 'react'
import { cn } from '@/utils/cn'

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'destructive' | 'gold'
  size?: 'sm' | 'md' | 'lg' | 'icon'
  isLoading?: boolean
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = 'primary',
      size = 'md',
      isLoading = false,
      children,
      disabled,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      'inline-flex items-center justify-center font-medium rounded-lg transition-colors duration-150 active:translate-y-px disabled:opacity-40 disabled:pointer-events-none select-none tracking-tight'

    const variants = {
      primary:
        'bg-amber-500 hover:bg-amber-400 text-stone-950 font-semibold border border-amber-400/80',
      gold:
        'bg-amber-500 hover:bg-amber-400 text-stone-950 font-bold border border-amber-400',
      secondary:
        'bg-stone-800 hover:bg-stone-700 text-stone-100 border border-stone-700 font-medium',
      outline:
        'border border-stone-800 hover:border-stone-600 bg-stone-900/90 hover:bg-stone-850 text-stone-200',
      ghost:
        'hover:bg-stone-800/80 text-stone-300 hover:text-white',
      destructive:
        'bg-red-950/80 hover:bg-red-900 text-red-200 border border-red-800/80',
    }

    const sizes = {
      sm: 'px-3 py-1.5 text-xs',
      md: 'px-4 py-2 text-sm',
      lg: 'px-6 py-2.5 text-base font-semibold',
      icon: 'h-9 w-9 p-1.5',
    }

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        {...props}
      >
        {isLoading ? (
          <span className="flex items-center gap-2">
            <svg
              className="animate-spin h-4 w-4 text-current"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <span>Please wait...</span>
          </span>
        ) : (
          children
        )}
      </button>
    )
  }
)

Button.displayName = 'Button'
