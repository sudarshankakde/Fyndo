import axios from 'axios'

export interface GeocodeResult {
  lat: number
  lon: number
  displayName: string
}

let lastRequestTime = 0

// Throttle requests to Nominatim to adhere to 1 req/sec usage policy
async function throttleNominatim(): Promise<void> {
  const now = Date.now()
  const elapsed = now - lastRequestTime
  if (elapsed < 1000) {
    await new Promise((resolve) => setTimeout(resolve, 1000 - elapsed))
  }
  lastRequestTime = Date.now()
}

export const geocodeAdapter = {
  async search(query: string): Promise<GeocodeResult[]> {
    if (!query || query.trim().length < 3) return []
    try {
      await throttleNominatim()
      const response = await axios.get('https://nominatim.openstreetmap.org/search', {
        params: {
          q: query.trim(),
          format: 'json',
          addressdetails: 1,
          limit: 5,
          countrycodes: 'in',
        },
        headers: {
          'Accept-Language': 'en',
        },
        timeout: 5000,
      })

      if (!Array.isArray(response.data)) return []

      return response.data.map((item: any) => ({
        lat: parseFloat(item.lat),
        lon: parseFloat(item.lon),
        displayName: item.display_name,
      }))
    } catch {
      return []
    }
  },

  async reverse(lat: number, lon: number): Promise<string> {
    try {
      await throttleNominatim()
      const response = await axios.get('https://nominatim.openstreetmap.org/reverse', {
        params: {
          lat,
          lon,
          format: 'json',
          addressdetails: 1,
        },
        headers: {
          'Accept-Language': 'en',
        },
        timeout: 5000,
      })

      return response.data?.display_name || ''
    } catch {
      return ''
    }
  },
}
