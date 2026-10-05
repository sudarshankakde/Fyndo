import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import { AuthSession, StaffSession, UserProfile } from '@/types/auth'

interface AuthState {
  token: string | null
  refreshToken: string | null
  user: UserProfile | null
  staff: StaffSession | null
  isAuthenticated: boolean
}

// Always start on login screen for role-wise navigation
const initialState: AuthState = {
  token: null,
  refreshToken: null,
  user: null,
  staff: null,
  isAuthenticated: false,
}

export const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setAuthSession: (state, action: PayloadAction<AuthSession>) => {
      state.token = action.payload.accessToken
      state.refreshToken = action.payload.refreshToken || null
      state.user = action.payload.user
      state.staff = null
      state.isAuthenticated = true

      localStorage.setItem('fyndo_token', action.payload.accessToken)
      if (action.payload.refreshToken) {
        localStorage.setItem('fyndo_refresh_token', action.payload.refreshToken)
      }
      localStorage.setItem('fyndo_user', JSON.stringify(action.payload.user))
      localStorage.removeItem('fyndo_staff')
    },
    setStaffSession: (state, action: PayloadAction<StaffSession>) => {
      state.token = action.payload.accessToken
      state.staff = action.payload
      state.user = null
      state.isAuthenticated = true

      localStorage.setItem('fyndo_token', action.payload.accessToken)
      localStorage.setItem('fyndo_staff', JSON.stringify(action.payload))
      localStorage.removeItem('fyndo_user')
    },
    logout: (state) => {
      state.token = null
      state.refreshToken = null
      state.user = null
      state.staff = null
      state.isAuthenticated = false

      localStorage.removeItem('fyndo_token')
      localStorage.removeItem('fyndo_refresh_token')
      localStorage.removeItem('fyndo_user')
      localStorage.removeItem('fyndo_staff')
    },
  },
})

export const { setAuthSession, setStaffSession, logout } = authSlice.actions
export default authSlice.reducer
