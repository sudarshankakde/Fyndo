import React from 'react'
import { Smartphone, QrCode, Play, Tag, MapPin, Store, ShieldCheck, ArrowRight } from 'lucide-react'
import { QRCodeSVG } from 'qrcode.react'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { useTranslation } from '@/hooks/useTranslation'
import { Link } from 'react-router-dom'

export const MobileAppShowcasePage: React.FC = () => {
  const { t } = useTranslation()
  const appInstallUrl = typeof window !== 'undefined' ? window.location.origin : 'https://fyndo.in'

  return (
    <div className="min-h-screen py-12 sm:py-16 space-y-12">
      {/* Top Architectural Notice Bar */}
      <div className="p-4 rounded-xl border border-stone-800 bg-stone-900/60 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded bg-stone-800 border border-stone-700 flex items-center justify-center text-amber-400 font-mono text-xs shrink-0">
            APP
          </div>
          <div>
            <h2 className="text-sm font-bold text-stone-100 font-display">
              {t.shopper_notice_title}
            </h2>
            <p className="text-xs text-stone-400 font-mono">
              {t.shopper_notice_desc}
            </p>
          </div>
        </div>

        <Link to="/merchant" className="shrink-0">
          <Button variant="outline" size="sm" className="text-xs font-mono">
            <span>MERCHANT STUDIO</span>
            <ArrowRight className="h-3 w-3 ml-1.5" />
          </Button>
        </Link>
      </div>

      {/* Asymmetric Split Layout: Left Spec & QR / Right Phone Viewport */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-start">
        {/* Left Column (7 cols): Editorial Typography & Hardware Anchor */}
        <div className="lg:col-span-7 space-y-8">
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <span className="font-mono text-[10px] uppercase tracking-widest text-amber-400 px-2 py-0.5 rounded border border-amber-800/60 bg-amber-950/20">
                MOBILE APP
              </span>
              <span className="font-mono text-xs text-stone-400">
                NAGPUR & MUMBAI
              </span>
            </div>

            <h1 className="text-3xl sm:text-5xl font-extrabold text-stone-100 font-display tracking-tight leading-[1.1]">
              Watch Short Deals. Walk In & Save.
            </h1>

            <p className="text-sm sm:text-base text-stone-400 leading-relaxed max-w-xl">
              Scroll through short videos filmed by real local stores in Nagpur and Mumbai. Discover fresh discounts within 2km to 10km and save digital coupons with rotating codes to show at the billing counter.
            </p>
          </div>

          {/* Architectural Feature Breakdown */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 font-mono text-xs">
            <div className="p-4 rounded-xl border border-stone-800 bg-stone-900/40 space-y-1.5">
              <div className="flex items-center gap-2 text-stone-200 font-bold">
                <MapPin className="h-3.5 w-3.5 text-amber-400" />
                <span>Nearby Deals</span>
              </div>
              <p className="text-stone-400 text-[11px] leading-normal">
                Discover discounts happening right now within 2km, 5km, or 10km of your location.
              </p>
            </div>

            <div className="p-4 rounded-xl border border-stone-800 bg-stone-900/40 space-y-1.5">
              <div className="flex items-center gap-2 text-stone-200 font-bold">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                <span>Rotating Code</span>
              </div>
              <p className="text-stone-400 text-[11px] leading-normal">
                Coupon codes refresh every 60 seconds so only real in-store shoppers can claim them.
              </p>
            </div>
          </div>

          {/* App Installation Anchor Box */}
          <div className="surface-card p-6 rounded-xl border border-stone-800 bg-stone-900/80 flex flex-col sm:flex-row items-center gap-6">
            <div className="p-3 bg-white rounded border border-stone-300 shrink-0">
              <QRCodeSVG value={appInstallUrl} size={110} level="M" />
            </div>
            <div className="space-y-2 text-center sm:text-left">
              <span className="font-mono text-[10px] uppercase tracking-wider text-amber-400 block">
                Get the Mobile App
              </span>
              <h3 className="text-base font-bold text-stone-100 font-display">
                {t.scan_qr_to_install}
              </h3>
              <p className="text-xs text-stone-400 max-w-sm">
                Scan this QR code with your phone camera to open Fyndo and start exploring local store deals immediately.
              </p>
            </div>
          </div>
        </div>

        {/* Right Column (5 cols): Bespoke Physical Smartphone Silhouette */}
        <div className="lg:col-span-5 flex justify-center">
          <div className="w-full max-w-xs aspect-reel rounded-[32px] border-2 border-stone-800 bg-stone-950 p-2.5 relative shadow-none">
            {/* Notch */}
            <div className="absolute top-4 left-1/2 -translate-x-1/2 h-3.5 w-24 bg-stone-900 rounded-full z-20" />

            {/* Video Viewport Frame */}
            <div className="relative w-full h-full rounded-[24px] overflow-hidden bg-stone-900 flex flex-col justify-between p-4">
              <img
                src="https://images.unsplash.com/photo-1601050690597-df0568f70950?w=600&auto=format&fit=crop"
                alt="Sitabuldi Sweets"
                className="absolute inset-0 w-full h-full object-cover filter brightness-[0.75]"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-stone-950 via-stone-950/20 to-black/40" />

              {/* Top Reel Meta */}
              <div className="relative z-10 flex items-center justify-between pt-6">
                <span className="font-mono text-[10px] font-bold text-amber-400 bg-stone-950/90 border border-stone-800 px-2 py-0.5 rounded">
                  450m • SITABULDI
                </span>
                <div className="h-6 w-6 rounded bg-stone-900/90 border border-stone-800 flex items-center justify-center text-stone-300">
                  <Play className="h-2.5 w-2.5 fill-current ml-0.5" />
                </div>
              </div>

              {/* Bottom In-Store Voucher Frame */}
              <div className="relative z-10 space-y-2">
                <div>
                  <h4 className="font-bold text-sm text-stone-100 font-display">Haldirams Sitabuldi</h4>
                  <p className="text-[11px] text-stone-300 line-clamp-1 font-mono">
                    Hot Crispy Jalebis 40% In-Store
                  </p>
                </div>

                <div className="p-2.5 rounded border border-stone-800 bg-stone-950/90 flex items-center justify-between">
                  <div>
                    <span className="font-mono text-[10px] font-bold text-amber-400 block">
                      40% OFF IN-STORE
                    </span>
                    <span className="font-mono text-[9px] text-stone-400">Min bill ₹200</span>
                  </div>
                  <span className="font-mono text-[9px] font-semibold px-2 py-1 rounded bg-amber-500 text-stone-950">
                    CLAIMED
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
