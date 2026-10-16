import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import { AuthSession, StaffSession, UserProfile } from '@/types/auth'
import { setAccessToken } from '@/services/http'

export type AuthBootStatus = 'booting' | 'authed' | 'anon'

export interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  user: UserProfile | null
  staff: StaffSession | null
  status: AuthBootStatus
  isAuthenticated: boolean
}

// BroadcastChannel for cross-tab session logout synchronization
const authChannel = typeof window !== 'undefined' && 'BroadcastChannel' in window
  ? new BroadcastChannel('fyndo_auth')
  : null

const initialState: AuthState = {
  accessToken: null,
  refreshToken: null,
  user: null,
  staff: null,
  status: 'booting',
  isAuthenticated: false,
}

export const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setAuthSession: (state, action: PayloadAction<AuthSession>) => {
      state.accessToken = action.payload.accessToken
      state.refreshToken = null
      state.user = action.payload.user
      state.staff = null
      state.status = 'authed'
      state.isAuthenticated = true

      setAccessToken(action.payload.accessToken)
    },
    setStaffSession: (state, action: PayloadAction<StaffSession>) => {
      state.accessToken = action.payload.accessToken
      state.refreshToken = null
      state.staff = action.payload
      state.user = null
      state.status = 'authed'
      state.isAuthenticated = true

      setAccessToken(action.payload.accessToken)
    },
    updateUser: (state, action: PayloadAction<Partial<UserProfile>>) => {
      if (state.user) {
        state.user = { ...state.user, ...action.payload }
      }
    },
    setBootComplete: (state, action: PayloadAction<boolean>) => {
      state.status = action.payload ? 'authed' : 'anon'
      state.isAuthenticated = action.payload
    },
    logout: (state) => {
      state.accessToken = null
      state.refreshToken = null
      state.user = null
      state.staff = null
      state.status = 'anon'
      state.isAuthenticated = false

      setAccessToken(null)
      localStorage.removeItem('fyndo_pos_store_phone')

      if (authChannel) {
        authChannel.postMessage({ type: 'LOGOUT' })
      }
    },
  },
})

export const { setAuthSession, setStaffSession, updateUser, setBootComplete, logout } = authSlice.actions
export default authSlice.reducer
