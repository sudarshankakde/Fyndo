import React, { useState } from 'react'
import { MapPin, Navigation, Search, AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { detectBetaCity } from '@/utils/geo'
import { geocodeAdapter } from '@/services/adapters/geocodeAdapter'
import { BETA_CITIES } from '@/config/constants'

export interface LocationPickerValue {
  latitude: number
  longitude: number
  city: string
  address: string
  source: 'gps' | 'map' | 'manual'
  isEntranceConfirmed: boolean
}

interface LocationPickerProps {
  value: LocationPickerValue
  onChange: (val: LocationPickerValue) => void
}

export const LocationPicker: React.FC<LocationPickerProps> = ({ value, onChange }) => {
  const [activeTab, setActiveTab] = useState<'GPS' | 'SEARCH' | 'MANUAL'>('GPS')
  const [isLocating, setIsLocating] = useState(false)
  const [gpsAccuracy, setGpsAccuracy] = useState<number | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const detectedCity = detectBetaCity(value.latitude, value.longitude)

  const handleRecordGps = () => {
    if (!navigator.geolocation) {
      setErrorMessage('Location services are not supported by your browser.')
      setActiveTab('SEARCH')
      return
    }

    setIsLocating(true)
    setErrorMessage(null)

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const { latitude, longitude, accuracy } = pos.coords
        setGpsAccuracy(accuracy)
        setIsLocating(false)

        const city = detectBetaCity(latitude, longitude) || 'Nagpur'
        let address = value.address
        try {
          address = await geocodeAdapter.reverse(latitude, longitude)
        } catch {
          // Best effort
        }

        onChange({
          ...value,
          latitude: Number(latitude.toFixed(6)),
          longitude: Number(longitude.toFixed(6)),
          city,
          address: address || value.address,
          source: 'gps',
        })
      },
      (_err) => {
        setIsLocating(false)
        setErrorMessage('Could not record your GPS location. Please allow location permissions or find on map.')
        setActiveTab('SEARCH')
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    )
  }

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!searchQuery.trim()) return

    setIsSearching(true)
    setErrorMessage(null)
    try {
      const results = await geocodeAdapter.search(searchQuery)
      setSearchResults(results)
      if (results.length === 0) {
        setErrorMessage('No locations found matching your search. Try a landmark or area name.')
      }
    } catch {
      setErrorMessage('Location search failed. Please try again.')
    } finally {
      setIsSearching(false)
    }
  }

  const handleSelectSearchResult = (res: any) => {
    const city = detectBetaCity(res.lat, res.lon) || 'Nagpur'
    onChange({
      ...value,
      latitude: Number(res.lat.toFixed(6)),
      longitude: Number(res.lon.toFixed(6)),
      city,
      address: res.displayName,
      source: 'map',
    })
    setSearchResults([])
  }

  const handleSetCityPreset = (cityKey: 'NAGPUR' | 'MUMBAI') => {
    const city = BETA_CITIES[cityKey]
    onChange({
      ...value,
      latitude: city.center.lat,
      longitude: city.center.lon,
      city: city.name,
      address: `${city.name} Central Market`,
      source: 'map',
    })
  }

  return (
    <div className="space-y-4 font-sans text-stone-900">
      {/* Permanent Shop Entrance Guidance Banner */}
      <div className="bg-amber-50 border border-amber-200 rounded-2xl p-3.5 flex items-start gap-2.5">
        <Navigation className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
        <p className="text-xs font-semibold text-amber-900 leading-relaxed">
          Please record the coordinates of your shop. Stand at the shop entrance for the best result.
        </p>
      </div>

      {/* Tabs */}
      <div className="grid grid-cols-3 p-1 bg-stone-100 rounded-xl text-xs font-bold border border-stone-200">
        <button
          type="button"
          onClick={() => setActiveTab('GPS')}
          className={`py-2 rounded-lg transition-all ${
            activeTab === 'GPS' ? 'bg-white text-stone-900 shadow-xs' : 'text-stone-500'
          }`}
        >
          My Location
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('SEARCH')}
          className={`py-2 rounded-lg transition-all ${
            activeTab === 'SEARCH' ? 'bg-white text-stone-900 shadow-xs' : 'text-stone-500'
          }`}
        >
          Search Place
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('MANUAL')}
          className={`py-2 rounded-lg transition-all ${
            activeTab === 'MANUAL' ? 'bg-white text-stone-900 shadow-xs' : 'text-stone-500'
          }`}
        >
          City Preset
        </button>
      </div>

      {errorMessage && (
        <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs font-medium flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 text-red-600" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Tab 1: Current GPS */}
      {activeTab === 'GPS' && (
        <div className="space-y-3">
          <Button
            type="button"
            onClick={handleRecordGps}
            isLoading={isLocating}
            className="w-full gap-2 py-3 bg-stone-900 hover:bg-stone-800 text-white"
          >
            <Navigation className="w-4 h-4" />
            <span>Record Entrance Location (GPS)</span>
          </Button>

          {gpsAccuracy !== null && (
            <p className="text-[11px] text-stone-500 text-center">
              GPS Accuracy: ±{Math.round(gpsAccuracy)} meters
              {gpsAccuracy > 50 && (
                <span className="text-amber-700 font-bold block mt-0.5">
                  Accuracy is lower than 50m. Step outdoors near the shop door for best fix.
                </span>
              )}
            </p>
          )}
        </div>
      )}

      {/* Tab 2: Search */}
      {activeTab === 'SEARCH' && (
        <div className="space-y-3">
          <form onSubmit={handleSearch} className="flex gap-2">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search area (e.g. Sitabuldi Nagpur, Dadar Mumbai)"
              className="flex-1 h-10 px-3.5 rounded-xl border border-stone-200 text-xs font-medium text-stone-900 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary shadow-2xs"
            />
            <Button type="submit" isLoading={isSearching} size="sm">
              <Search className="w-4 h-4" />
            </Button>
          </form>

          {searchResults.length > 0 && (
            <div className="border border-stone-200 rounded-xl divide-y divide-stone-100 max-h-40 overflow-y-auto bg-white shadow-2xs">
              {searchResults.map((res, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => handleSelectSearchResult(res)}
                  className="w-full p-2.5 text-left text-xs hover:bg-stone-50 flex items-start gap-2"
                >
                  <MapPin className="w-3.5 h-3.5 text-primary shrink-0 mt-0.5" />
                  <span className="truncate">{res.displayName}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 3: City Presets */}
      {activeTab === 'MANUAL' && (
        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => handleSetCityPreset('NAGPUR')}
            className="p-3 rounded-xl border border-stone-200 hover:border-primary bg-white text-left shadow-2xs transition-all"
          >
            <p className="text-xs font-extrabold text-stone-900">Nagpur Beta</p>
            <p className="text-[11px] text-stone-500">Sitabuldi Central Hub</p>
          </button>
          <button
            type="button"
            onClick={() => handleSetCityPreset('MUMBAI')}
            className="p-3 rounded-xl border border-stone-200 hover:border-primary bg-white text-left shadow-2xs transition-all"
          >
            <p className="text-xs font-extrabold text-stone-900">Mumbai Beta</p>
            <p className="text-[11px] text-stone-500">Dadar Central Market</p>
          </button>
        </div>
      )}

      {/* Recorded Coordinates Card */}
      <div className="bg-stone-50 rounded-2xl p-3.5 border border-stone-200 space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="font-bold text-stone-600">Entrance Coordinates</span>
          <span className="px-2 py-0.5 rounded-full bg-white text-stone-700 text-[10px] font-bold border border-stone-200">
            {value.source === 'gps' ? 'Phone GPS' : 'Placed on Map'}
          </span>
        </div>
        <div className="grid grid-cols-2 gap-2 font-mono text-xs font-bold text-stone-900">
          <div className="bg-white p-2 rounded-lg border border-stone-200">
            Lat: {value.latitude.toFixed(6)}
          </div>
          <div className="bg-white p-2 rounded-lg border border-stone-200">
            Lon: {value.longitude.toFixed(6)}
          </div>
        </div>

        {/* City verification tag */}
        {!detectedCity && (
          <div className="p-2.5 rounded-xl bg-amber-50 text-amber-800 text-xs font-medium border border-amber-200">
            ⚠️ Fyndo is currently active in Nagpur and Mumbai only during Beta.
          </div>
        )}
      </div>

      {/* Entrance Confirmation Checkbox */}
      <label className="flex items-start gap-2.5 p-3 rounded-xl bg-white border border-stone-200 shadow-2xs cursor-pointer select-none">
        <input
          type="checkbox"
          checked={value.isEntranceConfirmed}
          onChange={(e) => onChange({ ...value, isEntranceConfirmed: e.target.checked })}
          className="w-4 h-4 rounded border-stone-300 text-primary focus:ring-primary mt-0.5 cursor-pointer"
        />
        <span className="text-xs font-bold text-stone-800">
          This pin is at my shop entrance (required for in-store checkout accuracy)
        </span>
      </label>
    </div>
  )
}
