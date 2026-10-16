import React, { useState, useEffect } from 'react'
import { WifiOff } from 'lucide-react'

export const OfflineBanner: React.FC = () => {
  const [isOffline, setIsOffline] = useState(!navigator.onLine)

  useEffect(() => {
    const handleOnline = () => setIsOffline(false)
    const handleOffline = () => setIsOffline(true)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  if (!isOffline) return null

  return (
    <div
      role="status"
      aria-live="polite"
      className="bg-amber-500 text-stone-950 font-bold px-4 py-2 text-xs flex items-center justify-center gap-2 shadow-sm sticky top-0 z-50 animate-in fade-in"
    >
      <WifiOff className="w-4 h-4 shrink-0" />
      <span>You are currently offline. Please check your internet connection.</span>
    </div>
  )
}
