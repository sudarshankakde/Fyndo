import React, { useState, useEffect, useRef } from 'react'
import { Camera, CheckCircle2, AlertCircle, RotateCcw, MapPin, KeyRound } from 'lucide-react'
import confetti from 'canvas-confetti'
import { StaffSession } from '@/types/auth'
import { RedemptionVerifyResult } from '@/types/coupon'
import { redemptionService } from '@/services/redemptionService'
import { scannerAdapter } from '@/services/adapters/scannerAdapter'
import { Button } from '@/components/ui/Button'
import { formatRupees } from '@/utils/format'

interface PosScannerCardProps {
  staff: StaffSession
}

export const PosScannerCard: React.FC<PosScannerCardProps> = ({ staff }) => {
  const videoRef = useRef<HTMLVideoElement>(null)
  const lastPayloadRef = useRef<{ hash: string; time: number } | null>(null)

  const [mode, setMode] = useState<'SCAN' | 'MANUAL'>('SCAN')
  const [step, setStep] = useState<'VIEWFINDER' | 'CONFIRM' | 'RESULT'>('VIEWFINDER')

  // Location state (required upfront)
  const [coords, setCoords] = useState<{ lat: number; lon: number } | null>(null)
  const [locationError, setLocationError] = useState<string | null>(null)

  // Scanner & Confirmation state
  const [payloadToRedeem, setPayloadToRedeem] = useState<string>('')
  const [billAmount, setBillAmount] = useState<string>('')
  const [manualPin, setManualPin] = useState<string>('')
  const [manualCouponId, setManualCouponId] = useState<string>('')

  const [isVerifying, setIsVerifying] = useState(false)
  const [cameraError, setCameraError] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [result, setResult] = useState<RedemptionVerifyResult | null>(null)
  const [autoReturnTimer, setAutoReturnTimer] = useState<number | null>(null)

  // 1. Request location upfront
  const requestLocation = () => {
    setLocationError(null)
    if (!navigator.geolocation) {
      setLocationError('Geolocation is not supported on this browser.')
      return
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setCoords({ lat: pos.coords.latitude, lon: pos.coords.longitude })
        setLocationError(null)
      },
      () => {
        setLocationError(
          'Location access is required to verify store proximity. Please allow location permissions.'
        )
      },
      { enableHighAccuracy: true, timeout: 8000 }
    )
  }

  useEffect(() => {
    requestLocation()
  }, [])

  // 2. Camera Viewfinder management
  useEffect(() => {
    let isMounted = true
    if (mode === 'SCAN' && step === 'VIEWFINDER' && coords) {
      const initCamera = async () => {
        if (!videoRef.current) return
        try {
          setCameraError(null)
          await scannerAdapter.start(videoRef.current, (code) => {
            if (isMounted) handleCodeDetected(code)
          })
        } catch (err: any) {
          if (isMounted) {
            setCameraError(err.message || 'Camera permission denied or camera not found.')
          }
        }
      }
      initCamera()
    } else {
      scannerAdapter.stop()
    }

    return () => {
      isMounted = false
      scannerAdapter.stop()
    }
  }, [mode, step, coords])

  // 3. Auto-return timer on success
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>
    if (step === 'RESULT' && autoReturnTimer !== null && autoReturnTimer > 0) {
      timer = setTimeout(() => setAutoReturnTimer((prev) => (prev ? prev - 1 : 0)), 1000)
    } else if (step === 'RESULT' && autoReturnTimer === 0) {
      resetToScan()
    }
    return () => clearTimeout(timer)
  }, [step, autoReturnTimer])

  const handleCodeDetected = (code: string) => {
    const now = Date.now()
    if (lastPayloadRef.current && lastPayloadRef.current.hash === code && now - lastPayloadRef.current.time < 3000) {
      return
    }
    lastPayloadRef.current = { hash: code, time: now }
    scannerAdapter.stop()
    setPayloadToRedeem(code)
    setErrorMessage(null)
    setStep('CONFIRM')
  }

  const resetToScan = () => {
    setStep('VIEWFINDER')
    setPayloadToRedeem('')
    setBillAmount('')
    setManualPin('')
    setManualCouponId('')
    setErrorMessage(null)
    setResult(null)
    setAutoReturnTimer(null)
  }

  const handleConfirmRedemption = async () => {
    const numBill = parseFloat(billAmount)
    if (isNaN(numBill) || numBill <= 0) {
      setErrorMessage('Please enter a valid bill amount greater than ₹0.')
      return
    }
    if (!coords) {
      setErrorMessage('Location coordinates are required. Please re-enable location.')
      return
    }

    setIsVerifying(true)
    setErrorMessage(null)

    try {
      let res: RedemptionVerifyResult
      if (mode === 'MANUAL' && manualPin && manualCouponId) {
        res = await redemptionService.verifyPin({
          user_coupon_id: manualCouponId.trim(),
          backup_pin: manualPin.trim(),
          bill_amount: numBill,
          cashier_lat: coords.lat,
          cashier_lon: coords.lon,
        })
      } else {
        res = await redemptionService.verifyAndRedeem({
          qr_payload: payloadToRedeem,
          bill_amount: numBill,
          cashier_lat: coords.lat,
          cashier_lon: coords.lon,
        })
      }

      setResult(res)
      setStep('RESULT')
      setAutoReturnTimer(6)

      if ('vibrate' in navigator) navigator.vibrate([100, 50, 100])
      confetti({ particleCount: 75, spread: 65, origin: { y: 0.6 }, colors: ['#10B981', '#FF385C', '#F59E0B'] })
    } catch (err: any) {
      if (err.status === 409) {
        setErrorMessage('This voucher has already been redeemed earlier.')
      } else if (err.status === 410) {
        setErrorMessage('Code expired. Please ask the customer to refresh their screen.')
      } else if (err.status === 403) {
        setErrorMessage('This coupon belongs to a different store or cashier is outside store radius.')
      } else if (err.status === 400) {
        setErrorMessage(err.message || 'Bill amount is below the coupon minimum order requirement.')
      } else if (err.status === 422) {
        setErrorMessage('Invalid amount entered. Please check the bill value.')
      } else if (err.status === 429) {
        setErrorMessage('Too many verification attempts. Please wait a moment.')
      } else {
        setErrorMessage(err.message || 'Verification failed. Please check network and retry.')
      }
    } finally {
      setIsVerifying(false)
    }
  }

  // Blocker: Location Permission Denied
  if (locationError) {
    return (
      <div className="bg-white rounded-3xl border border-stone-200/80 p-8 shadow-card text-center space-y-4 max-w-md mx-auto font-sans">
        <div className="w-14 h-14 rounded-2xl bg-amber-50 text-amber-600 flex items-center justify-center mx-auto">
          <MapPin className="w-7 h-7" />
        </div>
        <div>
          <h2 className="text-lg font-black text-stone-900">Location Permission Required</h2>
          <p className="text-xs text-stone-500 mt-1 leading-relaxed">{locationError}</p>
        </div>
        <Button onClick={requestLocation} variant="primary" className="w-full text-xs font-bold">
          Enable Location & Retry
        </Button>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-3xl border border-stone-200/80 p-6 shadow-card space-y-5 font-sans text-stone-900">
      {/* Mode Toggle Bar */}
      <div className="flex items-center justify-between border-b border-stone-100 pb-3">
        <div className="flex gap-2">
          <button
            onClick={() => { setMode('SCAN'); resetToScan() }}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 ${
              mode === 'SCAN' ? 'bg-emerald-600 text-white shadow-xs' : 'bg-stone-100 text-stone-600'
            }`}
          >
            <Camera className="w-3.5 h-3.5" />
            <span>Camera Scanner</span>
          </button>
          <button
            onClick={() => { setMode('MANUAL'); setStep('CONFIRM'); setErrorMessage(null) }}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 ${
              mode === 'MANUAL' ? 'bg-emerald-600 text-white shadow-xs' : 'bg-stone-100 text-stone-600'
            }`}
          >
            <KeyRound className="w-3.5 h-3.5" />
            <span>Backup PIN Entry</span>
          </button>
        </div>
        {coords && (
          <span className="hidden sm:inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            GPS Locked
          </span>
        )}
      </div>

      {errorMessage && (
        <div className="p-3.5 rounded-2xl bg-red-50 border border-red-200 text-red-700 text-xs font-semibold flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Step 1: Scanner Viewfinder */}
      {step === 'VIEWFINDER' && mode === 'SCAN' && (
        <div className="space-y-4">
          <div className="relative aspect-4/3 w-full rounded-2xl overflow-hidden bg-stone-950 flex items-center justify-center border border-stone-200 shadow-inner">
            <video ref={videoRef} playsInline muted className="w-full h-full object-cover" />
            <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
              <div className="w-56 h-56 border-2 border-emerald-400/80 rounded-2xl relative">
                <div className="absolute top-0 left-0 w-4 h-4 border-t-4 border-l-4 border-emerald-400" />
                <div className="absolute top-0 right-0 w-4 h-4 border-t-4 border-r-4 border-emerald-400" />
                <div className="absolute bottom-0 left-0 w-4 h-4 border-b-4 border-l-4 border-emerald-400" />
                <div className="absolute bottom-0 right-0 w-4 h-4 border-b-4 border-r-4 border-emerald-400" />
                <div className="absolute inset-x-0 h-0.5 bg-emerald-400/60 animate-pulse top-1/2" />
              </div>
            </div>
            {cameraError && (
              <div className="absolute inset-0 bg-stone-900/90 p-6 flex flex-col items-center justify-center text-center text-white space-y-2 z-10">
                <Camera className="w-8 h-8 text-stone-400" />
                <p className="text-xs font-bold">{cameraError}</p>
                <Button size="sm" variant="outline" onClick={() => setMode('MANUAL')}>Switch to Manual Code</Button>
              </div>
            )}
          </div>
          <p className="text-xs text-stone-500 text-center">Point camera at customer's rotating 60s QR voucher.</p>
        </div>
      )}

      {/* Step 2: Bill Amount Entry & Explicit Confirmation */}
      {step === 'CONFIRM' && (
        <div className="space-y-4 max-w-sm mx-auto py-2">
          <div className="text-center">
            <span className="text-xs font-bold text-emerald-700 uppercase tracking-wider">Step 2: Enter Bill & Confirm</span>
            <h3 className="text-lg font-black text-stone-900 mt-1">
              {mode === 'MANUAL' ? 'Offline Voucher Redemption' : 'Voucher Scanned!'}
            </h3>
          </div>

          {mode === 'MANUAL' ? (
            <div className="space-y-3">
              <div>
                <label className="text-[11px] font-bold text-stone-600 uppercase block mb-1">Coupon Claim ID</label>
                <input
                  type="text"
                  value={manualCouponId}
                  onChange={(e) => setManualCouponId(e.target.value)}
                  placeholder="Paste coupon claim UUID"
                  className="h-10 w-full px-3 rounded-xl border border-stone-200 text-xs font-mono"
                />
              </div>
              <div>
                <label className="text-[11px] font-bold text-stone-600 uppercase block mb-1">4-Digit Backup PIN</label>
                <input
                  type="text"
                  maxLength={4}
                  value={manualPin}
                  onChange={(e) => setManualPin(e.target.value.replace(/\D/g, ''))}
                  placeholder="e.g. 1234"
                  className="h-10 w-full px-3 rounded-xl border border-stone-200 text-xs font-mono font-bold"
                />
              </div>
            </div>
          ) : (
            <div className="bg-stone-50 rounded-2xl p-3.5 border border-stone-200 text-center text-xs">
              <span className="text-stone-500">Scanned Payload: </span>
              <span className="font-mono font-bold text-stone-900 truncate block max-w-xs mx-auto">
                {payloadToRedeem.slice(0, 24)}...
              </span>
            </div>
          )}

          <div>
            <label className="text-[11px] font-bold text-stone-700 uppercase block mb-1">
              Total Bill Amount (₹) <span className="text-red-500">*</span>
            </label>
            <div className="relative flex items-center">
              <span className="absolute left-3.5 text-sm font-bold text-stone-400">₹</span>
              <input
                type="number"
                min="1"
                step="0.01"
                autoFocus
                value={billAmount}
                onChange={(e) => setBillAmount(e.target.value)}
                placeholder="Enter customer's final bill"
                className="h-12 w-full rounded-2xl border border-stone-200 pl-8 pr-4 text-base font-black text-stone-900 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 shadow-2xs"
              />
            </div>
          </div>

          <div className="flex gap-2 pt-2">
            <Button variant="outline" onClick={resetToScan} disabled={isVerifying} className="flex-1 text-xs">
              Cancel
            </Button>
            <Button
              variant="emerald"
              onClick={handleConfirmRedemption}
              disabled={isVerifying || !billAmount || parseFloat(billAmount) <= 0}
              isLoading={isVerifying}
              className="flex-1 text-xs font-bold"
            >
              Confirm & Redeem
            </Button>
          </div>
        </div>
      )}

      {/* Step 3: Result Screen */}
      {step === 'RESULT' && result && (
        <div className="text-center py-6 space-y-4 animate-in fade-in zoom-in-95">
          <div className="w-16 h-16 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto">
            <CheckCircle2 className="w-10 h-10" />
          </div>
          <div>
            <span className="text-xs font-bold text-emerald-700 uppercase tracking-wider">Coupon Verified & Applied</span>
            <h2 className="text-3xl font-black text-stone-900 mt-1">{formatRupees(result.discount_applied)} Discount</h2>
            <p className="text-sm font-bold text-stone-700 mt-1">{result.coupon_title}</p>
            <p className="text-xs text-stone-500 mt-0.5">
              Bill: {formatRupees(result.bill_amount)} • Customer: {result.customer_name || 'Verified Shopper'}
            </p>
          </div>
          <div className="pt-2">
            <Button onClick={resetToScan} variant="outline" className="gap-2 text-xs font-bold">
              <RotateCcw className="w-4 h-4" />
              <span>Next Customer ({autoReturnTimer}s)</span>
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
