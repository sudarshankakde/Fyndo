import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  LayoutDashboard,
  Film,
  PlusCircle,
  Store,
  KeyRound,
  BarChart3,
  CheckCircle2,
  AlertCircle,
  MapPin,
  RefreshCw,
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { merchantService, MerchantProfileData } from '@/services/merchantService'
import { MerchantOverviewView } from '@/components/merchant/dashboard/MerchantOverviewView'
import { MerchantOffersView } from '@/components/merchant/dashboard/MerchantOffersView'
import { MerchantStaffView } from '@/components/merchant/dashboard/MerchantStaffView'
import { MerchantProfileView } from '@/components/merchant/dashboard/MerchantProfileView'
import { MerchantAnalyticsView } from '@/components/merchant/dashboard/MerchantAnalyticsView'
import { SECTOR_DISPLAY_NAMES } from '@/config/constants'

export type MerchantTab = 'overview' | 'offers' | 'new-offer' | 'profile' | 'staff' | 'analytics'

export const MerchantPage: React.FC = () => {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<MerchantTab>('overview')

  const {
    data: profile,
    isLoading,
    refetch,
  } = useQuery<MerchantProfileData>({
    queryKey: ['merchant-profile'],
    queryFn: () => merchantService.getProfile(),
  })

  if (isLoading) {
    return (
      <div className="py-20 text-center space-y-3 font-sans">
        <RefreshCw className="w-8 h-8 text-primary animate-spin mx-auto" />
        <p className="text-xs text-stone-500 font-medium">Loading store manager...</p>
      </div>
    )
  }

  if (!profile) {
    return (
      <div className="max-w-md mx-auto text-center py-16 space-y-4 font-sans">
        <div className="w-16 h-16 rounded-full bg-primary/10 text-primary flex items-center justify-center mx-auto">
          <Store className="w-8 h-8" />
        </div>
        <h2 className="text-xl font-black text-stone-900">No Store Profile Registered</h2>
        <p className="text-xs text-stone-500 leading-relaxed">
          Register your retail store to publish short video deals and welcome verified walk-in customers.
        </p>
        <Button onClick={() => navigate('/merchant/onboarding')} className="w-full">
          Register Your Store
        </Button>
      </div>
    )
  }

  const isApproved = profile.kyc_status === 'APPROVED'

  const handleTabChange = (tab: MerchantTab) => {
    if (tab === 'new-offer') {
      navigate('/merchant/offers/new')
      return
    }
    setActiveTab(tab)
  }

  const navTabs = [
    { id: 'overview' as MerchantTab, label: 'Overview', icon: LayoutDashboard },
    { id: 'offers' as MerchantTab, label: 'Offers & Reels', icon: Film },
    { id: 'staff' as MerchantTab, label: 'Cashier Staff', icon: KeyRound },
    { id: 'profile' as MerchantTab, label: 'Store Profile', icon: Store },
    { id: 'analytics' as MerchantTab, label: 'Analytics', icon: BarChart3 },
  ]

  return (
    <div className="space-y-6 font-sans text-stone-900 pb-16">
      {/* Top Store Header Banner */}
      <div className="bg-white rounded-3xl border border-stone-200/80 p-6 shadow-card flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-start gap-4">
          <div className="w-14 h-14 rounded-2xl bg-primary/10 text-primary flex items-center justify-center font-extrabold text-2xl shrink-0">
            {profile.business_name ? profile.business_name[0] : 'S'}
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-xl font-extrabold text-stone-900 tracking-tight">
                {profile.business_name}
              </h1>
              {profile.kyc_status === 'APPROVED' && <Badge variant="success">Verified Store</Badge>}
              {profile.kyc_status === 'PENDING' && <Badge variant="amber">Under Review</Badge>}
              {profile.kyc_status === 'REJECTED' && <Badge variant="destructive">Needs Revision</Badge>}
            </div>

            <div className="flex items-center gap-3 text-xs text-stone-500 flex-wrap">
              <span>{SECTOR_DISPLAY_NAMES[profile.sector]?.en || profile.sector}</span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5 text-stone-400" />
                <span>{profile.city}</span>
              </span>
            </div>
          </div>
        </div>

        <Button
          disabled={!isApproved}
          onClick={() => navigate('/merchant/offers/new')}
          className="w-full md:w-auto gap-2 text-xs font-bold"
        >
          <PlusCircle className="w-4 h-4" />
          <span>Post Store Video & Offer</span>
        </Button>
      </div>

      {/* Navigation Tab Bar */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 border-b border-stone-200 no-scrollbar">
        {navTabs.map((tab) => {
          const Icon = tab.icon
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-2xl text-xs font-bold transition-all shrink-0 ${
                isActive
                  ? 'bg-stone-900 text-white shadow-xs'
                  : 'bg-white text-stone-600 hover:text-stone-900 border border-stone-200/80 hover:bg-stone-50'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          )
        })}
      </div>

      {/* Tab View Content */}
      <div className="pt-2">
        {activeTab === 'overview' && <MerchantOverviewView onNavigateTab={handleTabChange} />}
        {activeTab === 'offers' && <MerchantOffersView onPostNew={() => navigate('/merchant/offers/new')} />}
        {activeTab === 'staff' && <MerchantStaffView />}
        {activeTab === 'profile' && <MerchantProfileView />}
        {activeTab === 'analytics' && <MerchantAnalyticsView />}
      </div>
    </div>
  )
}
