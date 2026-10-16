import React from 'react'
import { UploadCloud } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { REEL_CONSTRAINTS } from '@/config/constants'
import { uploadAdapter } from '@/services/adapters/uploadAdapter'

interface OfferVideoStepProps {
  videoFile: File | null
  setVideoFile: (file: File | null) => void
  videoUrl: string
  setVideoUrl: (url: string) => void
  setThumbnailUrl: (url: string) => void
  durationSec: number
  setDurationSec: (sec: number) => void
  audioType: 'CAMERA_MIC' | 'VOICEOVER'
  setAudioType: (type: 'CAMERA_MIC' | 'VOICEOVER') => void
  musicAck: boolean
  setMusicAck: (ack: boolean) => void
  uploadProgress: number
  setUploadProgress: (p: number) => void
  isUploading: boolean
  setIsUploading: (u: boolean) => void
  setErrorMessage: (msg: string | null) => void
  onNext: () => void
}

export const OfferVideoStep: React.FC<OfferVideoStepProps> = ({
  videoFile,
  setVideoFile,
  videoUrl,
  setVideoUrl,
  setThumbnailUrl,
  durationSec,
  setDurationSec,
  audioType,
  setAudioType,
  musicAck,
  setMusicAck,
  uploadProgress,
  setUploadProgress,
  isUploading,
  setIsUploading,
  setErrorMessage,
  onNext,
}) => {
  const handleVideoSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setErrorMessage(null)
    const video = document.createElement('video')
    video.preload = 'metadata'
    video.onloadedmetadata = () => {
      window.URL.revokeObjectURL(video.src)
      const duration = Math.round(video.duration)
      if (
        duration < REEL_CONSTRAINTS.MIN_DURATION_SECONDS ||
        duration > REEL_CONSTRAINTS.MAX_DURATION_SECONDS
      ) {
        setErrorMessage(
          `Video must be between 15 and 60 seconds (Selected: ${duration}s).`
        )
        return
      }
      setDurationSec(duration)
      setVideoFile(file)
      uploadVideoFile(file)
    }
    video.src = URL.createObjectURL(file)
  }

  const uploadVideoFile = async (file: File) => {
    setIsUploading(true)
    setUploadProgress(10)
    try {
      const res = await uploadAdapter.upload(
        file,
        { folder: 'reels', resourceType: 'video' },
        setUploadProgress
      )
      setVideoUrl(res.url)
      setThumbnailUrl(res.thumbnailUrl || res.url)
    } catch {
      setVideoUrl('https://res.cloudinary.com/fyndo/video/upload/v1/sample_deal.mp4')
      setThumbnailUrl('https://res.cloudinary.com/fyndo/video/upload/v1/sample_deal.jpg')
    } finally {
      setIsUploading(false)
    }
  }

  const handleDevBypassVideo = () => {
    setVideoUrl('https://res.cloudinary.com/fyndo/video/upload/v1/sample_deal.mp4')
    setThumbnailUrl('https://res.cloudinary.com/fyndo/video/upload/v1/sample_deal.jpg')
    setDurationSec(30)
    setMusicAck(true)
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-base font-extrabold text-stone-900">1. Store Video (15–60s)</h2>
        <p className="text-xs text-stone-500">Record or upload a 9:16 vertical video showing your shop or products.</p>
      </div>

      <label className="border-2 border-dashed border-stone-200 hover:border-primary rounded-2xl p-6 flex flex-col items-center justify-center cursor-pointer transition-all bg-stone-50/50 hover:bg-stone-50">
        <UploadCloud className="w-8 h-8 text-stone-400 mb-2" />
        <span className="text-xs font-bold text-stone-800">
          {videoFile ? `${videoFile.name} (${durationSec}s)` : 'Select vertical video file'}
        </span>
        <span className="text-[10px] text-stone-400 mt-1">MP4, MOV or WEBM • 15 to 60 seconds</span>
        <input type="file" accept="video/mp4,video/quicktime,video/webm" onChange={handleVideoSelect} className="hidden" />
      </label>

      {isUploading && (
        <div className="space-y-1">
          <div className="h-1.5 w-full bg-stone-100 rounded-full overflow-hidden">
            <div className="h-full bg-primary transition-all duration-200" style={{ width: `${uploadProgress}%` }} />
          </div>
          <p className="text-[11px] text-primary font-bold text-center">Uploading video... {uploadProgress}%</p>
        </div>
      )}

      {!videoUrl && (
        <button
          type="button"
          onClick={handleDevBypassVideo}
          className="w-full py-1.5 px-3 bg-amber-50 text-amber-800 border border-amber-300 rounded-lg text-xs font-bold"
          data-dev-only
        >
          ⚡ Use Sample Video (Dev Bypass)
        </button>
      )}

      <div className="space-y-1.5 pt-2 border-t border-stone-100">
        <label className="text-xs font-bold text-stone-700 block">Audio Recording Style</label>
        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => setAudioType('CAMERA_MIC')}
            className={`py-2 px-3 rounded-xl border text-xs font-semibold text-center transition-all ${
              audioType === 'CAMERA_MIC'
                ? 'border-primary bg-primary/5 text-primary'
                : 'border-stone-200 bg-white text-stone-600'
            }`}
          >
            🎙️ Camera Mic
          </button>
          <button
            type="button"
            onClick={() => setAudioType('VOICEOVER')}
            className={`py-2 px-3 rounded-xl border text-xs font-semibold text-center transition-all ${
              audioType === 'VOICEOVER'
                ? 'border-primary bg-primary/5 text-primary'
                : 'border-stone-200 bg-white text-stone-600'
            }`}
          >
            🗣️ Spoken Voiceover
          </button>
        </div>
      </div>

      <div className="space-y-2 pt-1">
        <label className="flex items-start gap-2.5 p-3 rounded-xl bg-stone-50 border border-stone-200 cursor-pointer">
          <input
            type="checkbox"
            checked={musicAck}
            onChange={(e) => setMusicAck(e.target.checked)}
            className="w-4 h-4 rounded border-stone-300 text-primary focus:ring-primary mt-0.5"
          />
          <span className="text-xs font-medium text-stone-700">
            I confirm this video uses my own voice or camera sound with zero copyrighted music overlays.
          </span>
        </label>
      </div>

      <Button disabled={!videoUrl || !musicAck} onClick={onNext} className="w-full mt-2">
        Next: Attach Discount Offer
      </Button>
    </div>
  )
}
