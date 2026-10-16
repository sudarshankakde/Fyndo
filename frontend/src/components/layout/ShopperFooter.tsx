import React from 'react'
import { Link } from 'react-router-dom'
import { Store, ShieldCheck, ShieldAlert, Sparkles, MapPin } from 'lucide-react'

export const ShopperFooter: React.FC = () => {
  return (
    <footer className="bg-white border-t border-stone-200 mt-16 font-sans">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand Col */}
          <div className="space-y-3">
            <Link to="/" className="text-2xl font-extrabold tracking-tight text-stone-900 font-display">
              Fyndo<span className="text-primary">.</span>
            </Link>
            <p className="text-xs text-stone-500 leading-relaxed">
              Hyperlocal short video discovery and verified digital voucher redemption. Discover real in-store savings at shops near you.
            </p>
            <div className="flex items-center gap-2 text-xs font-semibold text-stone-700 bg-stone-50 p-2 rounded-xl border border-stone-200 w-fit">
              <MapPin className="w-3.5 h-3.5 text-primary" />
              <span>Nagpur & Mumbai Single-City Beta</span>
            </div>
          </div>

          {/* Quick Browse */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold text-stone-900 uppercase tracking-wider">Top Sectors</h4>
            <ul className="space-y-2 text-xs text-stone-500">
              <li><Link to="/" className="hover:text-primary transition-colors">🍔 Sweets & Fast Food (2–5 Days)</Link></li>
              <li><Link to="/" className="hover:text-primary transition-colors">👗 Fashion & Ethnic Wear (15 Days)</Link></li>
              <li><Link to="/" className="hover:text-primary transition-colors">👟 Footwear & Accessories (15 Days)</Link></li>
              <li><Link to="/" className="hover:text-primary transition-colors">📱 Electronics & Appliances (15 Days)</Link></li>
              <li><Link to="/" className="hover:text-primary transition-colors">🏡 Real Estate & Plots (Up to 60 Days)</Link></li>
            </ul>
          </div>

          {/* Partner & Merchant */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold text-stone-900 uppercase tracking-wider">For Local Businesses</h4>
            <ul className="space-y-2 text-xs text-stone-500">
              <li>
                <Link to="/merchant" className="hover:text-primary transition-colors flex items-center gap-1.5 font-medium">
                  <Store className="w-3.5 h-3.5 text-primary" />
                  <span>Merchant Studio Portal</span>
                </Link>
              </li>
              <li>
                <Link to="/merchant/onboarding" className="hover:text-primary transition-colors">
                  Register Your Store & KYC
                </Link>
              </li>
              <li>
                <Link to="/pos/login" className="hover:text-primary transition-colors flex items-center gap-1.5 font-medium">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Cashier Counter Scanner</span>
                </Link>
              </li>
            </ul>
          </div>

          {/* Security & Admin */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold text-stone-900 uppercase tracking-wider">Trust & Security</h4>
            <p className="text-xs text-stone-500 leading-relaxed">
              Every voucher features dynamic 60s security codes verified strictly within in-store radius limits. Zero screenshot fraud.
            </p>
            <div className="pt-2">
              <Link
                to="/admin/login"
                className="inline-flex items-center gap-1.5 text-xs font-bold text-stone-600 hover:text-stone-900 bg-stone-100 hover:bg-stone-200 px-3 py-1.5 rounded-full transition-colors"
              >
                <ShieldAlert className="w-3.5 h-3.5 text-amber-600" />
                <span>Super Admin Desk</span>
              </Link>
            </div>
          </div>
        </div>

        {/* Bottom Copyright */}
        <div className="border-t border-stone-200 mt-10 pt-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-stone-400">
          <p>© {new Date().getFullYear()} Fyndo Technologies India. All rights reserved.</p>
          <div className="flex items-center gap-4">
            <span>Built with ❤️ for Indian Local Commerce</span>
            <span>•</span>
            <span className="text-emerald-600 font-bold flex items-center gap-1">
              <Sparkles className="w-3 h-3" /> 100% Free for Beta Merchants
            </span>
          </div>
        </div>
      </div>
    </footer>
  )
}
