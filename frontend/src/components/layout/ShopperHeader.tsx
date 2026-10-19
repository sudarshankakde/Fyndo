import React, { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import {
  MapPin,
  Search,
  Ticket,
  User,
  Store,
  ChevronDown,
  Sparkles,
  LogOut,
  ShieldCheck,
} from 'lucide-react'
import { useAppDispatch, useAppSelector } from '@/store'
import { setLanguage, setLocation, setSelectedSector } from '@/store/slices/uiSlice'
import { logout } from '@/store/slices/authSlice'
import { SupportedLanguage } from '@/types/api'
import { BETA_CITIES, FEED_SECTORS, FeedSectorItem } from '@/config/constants'
import { authService } from '@/services/authService'

export const ShopperHeader: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const dispatch = useAppDispatch()
  const { language, location: userLoc, selectedSector } = useAppSelector((state) => state.ui)
  const { user, isAuthenticated } = useAppSelector((state) => state.auth)

  const [searchQuery, setSearchQuery] = useState('')
  const [isCityDropdownOpen, setIsCityDropdownOpen] = useState(false)
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false)

  const handleCitySelect = (cityName: 'NAGPUR' | 'MUMBAI') => {
    const cityData = BETA_CITIES[cityName]
    dispatch(
      setLocation({
        lat: cityData.center.lat,
        lon: cityData.center.lon,
        city: cityData.name,
        source: 'preset',
      })
    )
    setIsCityDropdownOpen(false)
  }

  const handleLogout = async () => {
    await authService.logout()
    dispatch(logout())
    setIsUserMenuOpen(false)
    navigate('/')
  }

  return (
    <header className="sticky top-0 z-40 bg-white border-b border-stone-200 shadow-2xs font-sans">
      {/* Top Banner Notice */}
      <div className="bg-primary text-white text-xs py-1.5 px-4 font-semibold text-center flex items-center justify-center gap-2">
        <Sparkles className="w-3.5 h-3.5 animate-pulse shrink-0" />
        <span>Single-City Beta Live in Nagpur & Mumbai! Discover exclusive in-store deals up to 50% OFF.</span>
      </div>

      {/* Main Desktop Header */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex items-center justify-between gap-4">
        {/* Brand & Location */}
        <div className="flex items-center gap-6 shrink-0">
          <Link to="/" className="text-2xl font-extrabold tracking-tight text-stone-900 font-display">
            Fyndo<span className="text-primary">.</span>
          </Link>

          {/* City Selector Dropdown */}
          <div className="relative">
            <button
              onClick={() => setIsCityDropdownOpen(!isCityDropdownOpen)}
              className="flex items-center gap-1.5 bg-stone-50 hover:bg-stone-100 px-3 py-1.5 rounded-full border border-stone-200 text-xs font-bold text-stone-800 transition-colors"
            >
              <MapPin className="w-3.5 h-3.5 text-primary shrink-0" />
              <span>{userLoc.city || 'Nagpur'}</span>
              <ChevronDown className="w-3 h-3 text-stone-400" />
            </button>

            {isCityDropdownOpen && (
              <div className="absolute left-0 mt-2 w-48 bg-white rounded-2xl border border-stone-200 shadow-lg py-1.5 z-50 animate-in fade-in zoom-in-95">
                <div className="px-3 py-1.5 text-[10px] font-bold text-stone-400 uppercase tracking-wider">
                  Select Beta City
                </div>
                <button
                  onClick={() => handleCitySelect('NAGPUR')}
                  className="w-full text-left px-3.5 py-2 text-xs font-bold text-stone-800 hover:bg-stone-50 flex items-center justify-between"
                >
                  <span>Nagpur (Central & Sadar)</span>
                  {userLoc.city === 'Nagpur' && <span className="w-2 h-2 rounded-full bg-primary" />}
                </button>
                <button
                  onClick={() => handleCitySelect('MUMBAI')}
                  className="w-full text-left px-3.5 py-2 text-xs font-bold text-stone-800 hover:bg-stone-50 flex items-center justify-between"
                >
                  <span>Mumbai (Bandra & Dadar)</span>
                  {userLoc.city === 'Mumbai' && <span className="w-2 h-2 rounded-full bg-primary" />}
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Global Desktop Search Input */}
        <div className="flex-1 max-w-2xl relative hidden md:block">
          <div className="relative flex items-center">
            <Search className="absolute left-3.5 w-4 h-4 text-stone-400 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search stores, video deals, sweets, ethnic wear, shoes, electronics..."
              className="w-full h-11 pl-10 pr-24 rounded-full border border-stone-200 bg-stone-50 focus:bg-white text-xs font-semibold text-stone-900 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all shadow-2xs"
            />
            <span className="absolute right-3.5 px-2 py-0.5 rounded-md bg-stone-200/60 text-[10px] font-mono text-stone-500 font-bold">
              Explore
            </span>
          </div>
        </div>

        {/* Right Navigation Actions */}
        <div className="flex items-center gap-3">
          {/* Language Selector Pills */}
          <div className="hidden lg:flex items-center bg-stone-100 p-0.5 rounded-full border border-stone-200 text-[11px] font-bold notranslate">
            {(['en', 'hi', 'mr'] as SupportedLanguage[]).map((lang) => (
              <button
                key={lang}
                onClick={() => dispatch(setLanguage(lang))}
                className={`px-2.5 py-1 rounded-full uppercase transition-all ${
                  language === lang
                    ? 'bg-primary text-white shadow-xs'
                    : 'text-stone-500 hover:text-stone-900'
                }`}
              >
                {lang}
              </button>
            ))}
          </div>

          {/* Partner / Merchant Studio Link */}
          <Link
            to="/merchant"
            className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-stone-200 bg-stone-50 hover:bg-stone-100 text-xs font-bold text-stone-700 transition-colors"
          >
            <Store className="w-3.5 h-3.5 text-primary" />
            <span>Store Studio</span>
          </Link>

          {/* My Wallet Button */}
          <Link
            to="/wallet"
            className={`flex items-center gap-1.5 px-4 py-2 rounded-full text-xs font-bold transition-all shadow-2xs ${
              location.pathname === '/wallet'
                ? 'bg-primary text-white shadow-sm'
                : 'bg-white border border-stone-200 text-stone-800 hover:border-primary'
            }`}
          >
            <Ticket className="w-4 h-4 text-amber-500" />
            <span>My Savings</span>
          </Link>

          {/* User Profile / Login Dropdown */}
          {isAuthenticated ? (
            <div className="relative">
              <button
                onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                className="flex items-center gap-2 p-1.5 rounded-full hover:bg-stone-100 transition-colors"
              >
                <div className="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-xs">
                  {user?.full_name ? user.full_name.charAt(0).toUpperCase() : 'U'}
                </div>
              </button>

              {isUserMenuOpen && (
                <div className="absolute right-0 mt-2 w-52 bg-white rounded-2xl border border-stone-200 shadow-xl py-2 z-50 animate-in fade-in zoom-in-95">
                  <div className="px-4 py-2 border-b border-stone-100">
                    <p className="text-xs font-bold text-stone-900 truncate">{user?.full_name || 'Shopper'}</p>
                    <p className="text-[11px] text-stone-400 font-mono">{user?.phone}</p>
                  </div>
                  <Link
                    to="/profile"
                    onClick={() => setIsUserMenuOpen(false)}
                    className="flex items-center gap-2 px-4 py-2 text-xs font-semibold text-stone-700 hover:bg-stone-50"
                  >
                    <User className="w-4 h-4 text-stone-400" />
                    <span>My Profile</span>
                  </Link>
                  <Link
                    to="/wallet"
                    onClick={() => setIsUserMenuOpen(false)}
                    className="flex items-center gap-2 px-4 py-2 text-xs font-semibold text-stone-700 hover:bg-stone-50"
                  >
                    <Ticket className="w-4 h-4 text-stone-400" />
                    <span>Claimed Vouchers</span>
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="w-full text-left flex items-center gap-2 px-4 py-2 text-xs font-semibold text-red-600 hover:bg-red-50 border-t border-stone-100 mt-1"
                  >
                    <LogOut className="w-4 h-4 text-red-500" />
                    <span>Sign Out</span>
                  </button>
                </div>
              )}
            </div>
          ) : (
            <Link
              to="/login"
              className="px-4 py-2 rounded-full bg-stone-900 hover:bg-black text-white text-xs font-bold shadow-sm transition-all"
            >
              Sign In
            </Link>
          )}
        </div>
      </div>

      {/* Categories Bar (Amazon / Flipkart Style) */}
      <div className="bg-stone-50/80 border-t border-stone-200/80 px-4 sm:px-6 lg:px-8 py-2 overflow-x-auto no-scrollbar">
        <div className="max-w-7xl mx-auto flex items-center gap-2 text-xs font-bold text-stone-600">
          <button
            onClick={() => dispatch(setSelectedSector(null))}
            className={`px-3 py-1 rounded-full whitespace-nowrap transition-all ${
              selectedSector === null
                ? 'bg-stone-900 text-white shadow-xs'
                : 'hover:bg-white hover:text-stone-900'
            }`}
          >
            🔥 All Deals
          </button>
          {FEED_SECTORS.map((s: FeedSectorItem) => (
            <button
              key={s.value}
              onClick={() => dispatch(setSelectedSector(s.value))}
              className={`px-3 py-1 rounded-full whitespace-nowrap transition-all ${
                selectedSector === s.value
                  ? 'bg-primary text-white shadow-xs'
                  : 'hover:bg-white hover:text-stone-900'
              }`}
            >
              {s.icon} {s.label}
            </button>
          ))}
          <div className="h-4 w-px bg-stone-300 mx-1 shrink-0" />
          <Link
            to="/pos/login"
            className="flex items-center gap-1 px-3 py-1 text-stone-500 hover:text-stone-900 whitespace-nowrap"
          >
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            <span>Counter POS</span>
          </Link>
        </div>
      </div>
    </header>
  )
}
