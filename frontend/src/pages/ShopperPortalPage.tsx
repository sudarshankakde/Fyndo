import React, { useState } from 'react'
import { Film, Wallet, MapPin } from 'lucide-react'
import { FeedPage } from '@/pages/FeedPage'
import { WalletPage } from '@/pages/WalletPage'

export const ShopperPortalPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'FEED' | 'WALLET'>('FEED')

  return (
    <div className="space-y-4 max-w-2xl mx-auto py-4">
      {/* Top Segmented Tab Switcher */}
      <div className="flex rounded-lg bg-stone-900 border border-stone-800 p-1 font-mono text-xs max-w-md mx-auto">
        <button
          type="button"
          onClick={() => setActiveTab('FEED')}
          className={`flex-1 py-1.5 rounded flex items-center justify-center gap-1.5 transition-colors ${
            activeTab === 'FEED'
              ? 'bg-stone-850 text-amber-400 font-bold border border-stone-700'
              : 'text-stone-400 hover:text-stone-200'
          }`}
        >
          <Film className="h-3.5 w-3.5" />
          <span>Nearby Deals Feed</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('WALLET')}
          className={`flex-1 py-1.5 rounded flex items-center justify-center gap-1.5 transition-colors ${
            activeTab === 'WALLET'
              ? 'bg-stone-850 text-amber-400 font-bold border border-stone-700'
              : 'text-stone-400 hover:text-stone-200'
          }`}
        >
          <Wallet className="h-3.5 w-3.5" />
          <span>My Saved Coupons</span>
        </button>
      </div>

      {/* Render Selected View */}
      {activeTab === 'FEED' ? <FeedPage /> : <WalletPage />}
    </div>
  )
}
