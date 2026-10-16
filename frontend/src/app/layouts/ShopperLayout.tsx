import React from 'react'
import { Outlet } from 'react-router-dom'
import { ShopperHeader } from '@/components/layout/ShopperHeader'
import { ShopperFooter } from '@/components/layout/ShopperFooter'
import { DynamicQrModal } from '@/components/coupon/DynamicQrModal'

export const ShopperLayout: React.FC = () => {
  return (
    <div className="min-h-screen bg-[#FAFAFA] flex flex-col font-sans text-stone-900 selection:bg-rose-100 selection:text-rose-600">
      {/* Full-Width Desktop Navigation Bar */}
      <ShopperHeader />

      {/* Main Content Viewport */}
      <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <Outlet />
      </main>

      {/* Global Desktop Footer */}
      <ShopperFooter />

      {/* Dynamic Security QR Code Modal */}
      <DynamicQrModal />
    </div>
  )
}
