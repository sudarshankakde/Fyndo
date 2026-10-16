import React, { useState, useRef } from 'react'
import { UploadCloud } from 'lucide-react'
import { Button } from '@/components/ui/Button'

interface MerchantVideoUploaderProps {
  selectedFile: File | null
  previewUrl: string | null
  videoFileName: string | null
  onSelectFile: (file: File) => void
  onUseSample: (name: string, url: string) => void
}

export const MerchantVideoUploader: React.FC<MerchantVideoUploaderProps> = ({
  selectedFile,
  previewUrl,
  videoFileName,
  onSelectFile,
  onUseSample,
}) => {
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) onSelectFile(file)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files?.[0]
    if (file && file.type.startsWith('video/')) {
      onSelectFile(file)
    }
  }

  return (
    <div className="space-y-1.5">
      <input
        ref={fileInputRef}
        type="file"
        accept="video/mp4,video/quicktime,video/webm,video/m4v"
        className="hidden"
        onChange={handleFileChange}
      />

      <label className="font-mono text-xs text-stone-300 block">
        15–60s Video Reel (Raw Store Audio Only)
      </label>

      {previewUrl ? (
        <div className="border border-stone-800 rounded-xl p-4 bg-stone-900/60 space-y-3">
          <video
            src={previewUrl}
            controls
            className="w-full max-h-56 rounded-lg object-contain bg-black"
          />
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="text-stone-300 truncate max-w-[260px]">{videoFileName}</span>
            {selectedFile && (
              <span className="text-stone-500">
                {(selectedFile.size / (1024 * 1024)).toFixed(1)} MB
              </span>
            )}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => fileInputRef.current?.click()}
              className="text-xs font-mono"
            >
              Change Video
            </Button>
          </div>
        </div>
      ) : (
        <div
          onDragOver={(e) => {
            e.preventDefault()
            setIsDragging(true)
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border border-dashed rounded-xl p-6 text-center space-y-2 cursor-pointer transition-colors ${
            isDragging
              ? 'border-amber-400 bg-amber-950/20'
              : 'border-stone-800 bg-stone-900/40 hover:border-amber-500/50 hover:bg-stone-900/60'
          }`}
        >
          <UploadCloud className="h-8 w-8 text-amber-400 mx-auto" />
          <p className="text-xs text-stone-200 font-medium">
            Click to browse or drag & drop your video here
          </p>
          <p className="text-[11px] text-stone-400">
            Supports MP4, MOV, WebM (15–60s). Only authentic camera audio or voiceover.
          </p>
          <div className="pt-2 flex justify-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={(e) => {
                e.stopPropagation()
                fileInputRef.current?.click()
              }}
              className="text-xs font-mono"
            >
              Choose Video File
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation()
                onUseSample(
                  'sample_store_reel.mp4',
                  'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/WeAreGoingOnBullrun.mp4'
                )
              }}
              className="text-xs text-amber-400 font-mono"
            >
              Use Sample Reel
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
