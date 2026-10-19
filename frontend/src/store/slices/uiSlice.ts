import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import { SupportedLanguage } from '@/types/api'
import { BETA_CITIES, DEFAULT_RADIUS_KM } from '@/config/constants'

export type LocationSource = 'gps' | 'preset' | 'manual'

export interface UserLocation {
  lat: number
  lon: number
  source: LocationSource
  city: string
}

interface UiState {
  language: SupportedLanguage
  location: UserLocation
  radiusKm: number
  selectedSector: string | null
  activeUserCouponId: string | null
  isQrModalOpen: boolean
}

const savedLang = (typeof window !== 'undefined' && (localStorage.getItem('fyndo_lang') as SupportedLanguage)) || 'en'

const initialState: UiState = {
  language: savedLang,
  location: {
    lat: BETA_CITIES.NAGPUR.center.lat,
    lon: BETA_CITIES.NAGPUR.center.lon,
    source: 'preset',
    city: 'Nagpur',
  },
  radiusKm: DEFAULT_RADIUS_KM,
  selectedSector: null,
  activeUserCouponId: null,
  isQrModalOpen: false,
}

export const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    setLanguage: (state, action: PayloadAction<SupportedLanguage>) => {
      state.language = action.payload
      localStorage.setItem('fyndo_lang', action.payload)
    },
    setLocation: (state, action: PayloadAction<UserLocation>) => {
      state.location = action.payload
    },
    setRadiusKm: (state, action: PayloadAction<number>) => {
      state.radiusKm = action.payload
    },
    setSelectedSector: (state, action: PayloadAction<string | null>) => {
      state.selectedSector = action.payload
    },
    openQrModal: (state, action: PayloadAction<string>) => {
      state.activeUserCouponId = action.payload
      state.isQrModalOpen = true
    },
    closeQrModal: (state) => {
      state.isQrModalOpen = false
      state.activeUserCouponId = null
    },
  },
})

export const {
  setLanguage,
  setLocation,
  setRadiusKm,
  setSelectedSector,
  openQrModal,
  closeQrModal,
} = uiSlice.actions

export default uiSlice.reducer
