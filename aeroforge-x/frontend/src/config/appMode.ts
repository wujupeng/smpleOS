export const APP_MODE = (import.meta.env.VITE_APP_MODE || 'demo') as 'demo' | 'live'

export const isDemoMode = () => APP_MODE === 'demo'
export const isLiveMode = () => APP_MODE === 'live'

export function getApiBaseUrl(): string {
  if (isLiveMode()) {
    return import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001'
  }
  return ''
}

export function shouldUseMockData(): boolean {
  return isDemoMode()
}