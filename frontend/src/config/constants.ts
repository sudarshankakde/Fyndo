/**
 * System constants for Fyndo Platform (Single-City Beta: Nagpur / Mumbai).
 * Canonical rules from docs/01_Product_Requirements.md and docs/03_Features.md.
 */

export interface CityBoundingBox {
  name: string
  center: { lat: number; lon: number }
  bounds: { minLat: number; maxLat: number; minLon: number; maxLon: number }
}

export const BETA_CITIES: Record<string, CityBoundingBox> = {
  NAGPUR: {
    name: 'Nagpur',
    center: { lat: 21.1458, lon: 79.0882 }, // Sitabuldi
    bounds: { minLat: 21.00, maxLat: 21.30, minLon: 78.90, maxLon: 79.25 },
  },
  MUMBAI: {
    name: 'Mumbai',
    center: { lat: 19.0178, lon: 72.8478 }, // Dadar
    bounds: { minLat: 18.85, maxLat: 19.35, minLon: 72.70, maxLon: 73.10 },
  },
}

export const SECTOR_VALIDITY_CEILINGS: Record<string, number> = {
  FOOD: 5,
  FASHION: 15,
  FOOTWEAR: 15,
  ELECTRONICS: 15,
  REAL_ESTATE: 60,
}

export const SECTOR_DISPLAY_NAMES: Record<string, { en: string; hi: string; mr: string }> = {
  FOOD: { en: 'Food & Dining', hi: 'भोजन और रेस्टोरेंट', mr: 'खाद्य आणि उपहारगृह' },
  FASHION: { en: 'Clothing & Fashion', hi: 'कपड़े और फैशन', mr: 'कपडे आणि फॅशन' },
  FOOTWEAR: { en: 'Shoes & Footwear', hi: 'जूते और चप्पल', mr: 'पादत्राणे आणि शूज' },
  ELECTRONICS: { en: 'Electronics & Mobiles', hi: 'इलेक्ट्रॉनिक्स और मोबाइल', mr: 'इलेक्ट्रॉनिक्स आणि मोबाईल्स' },
  REAL_ESTATE: { en: 'Property & Real Estate', hi: 'प्रॉपर्टी और जमीन', mr: 'रिअल इस्टेट आणि मालमत्ता' },
}

export interface FeedSectorItem {
  value: string
  label: string
  icon: string
}

export const FEED_SECTORS: FeedSectorItem[] = [
  { value: 'FOOD', label: 'Food & Dining', icon: '🍔' },
  { value: 'FASHION', label: 'Clothing & Fashion', icon: '👗' },
  { value: 'FOOTWEAR', label: 'Shoes & Footwear', icon: '👟' },
  { value: 'ELECTRONICS', label: 'Electronics', icon: '📱' },
  { value: 'REAL_ESTATE', label: 'Real Estate', icon: '🏢' },
]

export const REEL_CONSTRAINTS = {
  MIN_DURATION_SECONDS: 15,
  MAX_DURATION_SECONDS: 60,
  ASPECT_RATIO: 9 / 16,
  MAX_FILE_SIZE_BYTES: 100 * 1024 * 1024, // 100MB
}

export const IDLE_LOCK_TIMEOUT_MS = {
  POS: 10 * 60 * 1000, // 10 minutes
  ADMIN: 15 * 60 * 1000, // 15 minutes
}

export const DEFAULT_RADIUS_KM = 5
export const RADIUS_OPTIONS = [2, 5, 10]
