import { createSlice, PayloadAction } from '@reduxjs/toolkit'

export type ScannerStatus = 'idle' | 'scanning' | 'verifying' | 'success' | 'error'

interface ScannerState {
  status: ScannerStatus
  lastPayloadHash: string | null
  lastScanAt: number | null
  errorMessage: string | null
}

const initialState: ScannerState = {
  status: 'idle',
  lastPayloadHash: null,
  lastScanAt: null,
  errorMessage: null,
}

export const scannerSlice = createSlice({
  name: 'scanner',
  initialState,
  reducers: {
    setScannerStatus: (state, action: PayloadAction<ScannerStatus>) => {
      state.status = action.payload
      if (action.payload === 'scanning' || action.payload === 'idle') {
        state.errorMessage = null
      }
    },
    recordScan: (state, action: PayloadAction<{ payloadHash: string; timestamp: number }>) => {
      state.lastPayloadHash = action.payload.payloadHash
      state.lastScanAt = action.payload.timestamp
      state.status = 'verifying'
    },
    setScannerError: (state, action: PayloadAction<string>) => {
      state.status = 'error'
      state.errorMessage = action.payload
    },
    resetScanner: (state) => {
      state.status = 'idle'
      state.lastPayloadHash = null
      state.lastScanAt = null
      state.errorMessage = null
    },
  },
})

export const { setScannerStatus, recordScan, setScannerError, resetScanner } = scannerSlice.actions
export default scannerSlice.reducer
