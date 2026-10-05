import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import { SupportedLanguage } from '@/types/api'

interface UiState {
  language: SupportedLanguage
  userLatitude: number
  userLongitude: number
  radiusKm: number
  selectedSector: string | null
  isAuthModalOpen: boolean
  isQrModalOpen: boolean
  activeUserCouponId: string | null
}

const savedLang = (localStorage.getItem('fyndo_lang') as SupportedLanguage) || 'en'

const initialState: UiState = {
  language: savedLang,
  userLatitude: 21.1458,  // Sitabuldi, Nagpur Beta epicenter
  userLongitude: 79.0882,
  radiusKm: 5,
  selectedSector: null,
  isAuthModalOpen: false,
  isQrModalOpen: false,
  activeUserCouponId: null,
}

export const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    setLanguage: (state, action: PayloadAction<SupportedLanguage>) => {
      state.language = action.payload
      localStorage.setItem('fyndo_lang', action.payload)
    },
    setUserLocation: (state, action: PayloadAction<{ lat: number; lon: number }>) => {
      state.userLatitude = action.payload.lat
      state.userLongitude = action.payload.lon
    },
    setRadiusKm: (state, action: PayloadAction<number>) => {
      state.radiusKm = action.payload
    },
    setSelectedSector: (state, action: PayloadAction<string | null>) => {
      state.selectedSector = action.payload
    },
    setAuthModalOpen: (state, action: PayloadAction<boolean>) => {
      state.isAuthModalOpen = action.payload
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
  setUserLocation,
  setRadiusKm,
  setSelectedSector,
  setAuthModalOpen,
  openQrModal,
  closeQrModal,
} = uiSlice.actions

export default uiSlice.reducer
