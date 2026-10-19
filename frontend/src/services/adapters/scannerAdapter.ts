export interface ScannerAdapter {
  start: (videoEl: HTMLVideoElement, onCode: (code: string) => void) => Promise<void>
  stop: () => void
}

let activeStream: MediaStream | null = null
let animationFrameId: number | null = null

export const scannerAdapter: ScannerAdapter = {
  async start(videoEl: HTMLVideoElement, onCode: (code: string) => void): Promise<void> {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error('Camera access is not supported by your browser.')
    }

    // Stop any existing streams
    scannerAdapter.stop()

    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: { ideal: 'environment' },
        width: { ideal: 1280 },
        height: { ideal: 720 },
      },
      audio: false,
    })

    activeStream = stream
    videoEl.srcObject = stream
    await videoEl.play()

    // Native BarcodeDetector API check
    const hasBarcodeDetector = 'BarcodeDetector' in window
    let detector: any = null
    if (hasBarcodeDetector) {
      try {
        const BarcodeDetectorClass = (window as any).BarcodeDetector
        detector = new BarcodeDetectorClass({ formats: ['qr_code'] })
      } catch {
        detector = null
      }
    }

    const checkFrame = async () => {
      if (!videoEl || videoEl.readyState < 2) {
        animationFrameId = requestAnimationFrame(checkFrame)
        return
      }

      if (detector) {
        try {
          const barcodes = await detector.detect(videoEl)
          if (barcodes.length > 0 && barcodes[0].rawValue) {
            onCode(barcodes[0].rawValue)
          }
        } catch {
          // Ignore individual frame detection failures
        }
      }

      animationFrameId = requestAnimationFrame(checkFrame)
    }

    animationFrameId = requestAnimationFrame(checkFrame)
  },

  stop(): void {
    if (animationFrameId !== null) {
      cancelAnimationFrame(animationFrameId)
      animationFrameId = null
    }

    if (activeStream) {
      activeStream.getTracks().forEach((track) => track.stop())
      activeStream = null
    }
  },
}
