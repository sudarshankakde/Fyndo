import axios from 'axios'
import { merchantService } from '../merchantService'

export interface UploadOptions {
  folder: 'reels' | 'kyc'
  resourceType?: 'video' | 'image'
}

export interface UploadResult {
  url: string
  publicId: string
  durationSec?: number
  thumbnailUrl?: string
}

export const uploadAdapter = {
  async upload(
    file: File,
    options: UploadOptions,
    onProgress?: (pct: number) => void,
    signal?: AbortSignal
  ): Promise<UploadResult> {
    const resourceType = options.resourceType || (file.type.startsWith('image/') ? 'image' : 'video')
    
    // 1. Fetch secure upload signature from backend
    const signData = await merchantService.getUploadSignature(options.folder, resourceType)

    // 2. Prepare multipart upload to Cloudinary directly
    const formData = new FormData()
    formData.append('file', file)
    formData.append('api_key', signData.api_key)
    formData.append('timestamp', signData.timestamp.toString())
    formData.append('signature', signData.signature)
    formData.append('folder', signData.folder)

    const response = await axios.post(signData.upload_url, formData, {
      signal,
      onUploadProgress: (evt) => {
        if (evt.total && onProgress) {
          const percent = Math.round((evt.loaded * 100) / evt.total)
          onProgress(percent)
        }
      },
    })

    const secureUrl = response.data.secure_url as string
    const publicId = response.data.public_id as string
    const duration = response.data.duration ? Math.round(response.data.duration) : undefined

    // Derive video poster thumbnail via Cloudinary URL transformation without a second upload
    let thumbnailUrl = secureUrl
    if (resourceType === 'video') {
      thumbnailUrl = secureUrl.replace(/\.[^/.]+$/, '.jpg')
    }

    return {
      url: secureUrl,
      publicId,
      durationSec: duration,
      thumbnailUrl,
    }
  },
}
