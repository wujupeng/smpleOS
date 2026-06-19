import { useRef, useCallback, useEffect, useState } from 'react'

interface TouchHandlers {
  onSwipeLeft?: () => void
  onSwipeRight?: () => void
  onPinch?: (scale: number) => void
}

const SWIPE_THRESHOLD = 50
const PINCH_THRESHOLD = 10

export function useTouchGesture(handlers: TouchHandlers) {
  const ref = useRef<HTMLDivElement>(null)
  const touchStart = useRef<{ x: number; y: number; distance?: number } | null>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    const handleTouchStart = (e: TouchEvent) => {
      if (e.touches.length === 1) {
        touchStart.current = { x: e.touches[0].clientX, y: e.touches[0].clientY }
      } else if (e.touches.length === 2) {
        const dx = e.touches[0].clientX - e.touches[1].clientX
        const dy = e.touches[0].clientY - e.touches[1].clientY
        touchStart.current = {
          x: (e.touches[0].clientX + e.touches[1].clientX) / 2,
          y: (e.touches[0].clientY + e.touches[1].clientY) / 2,
          distance: Math.sqrt(dx * dx + dy * dy),
        }
      }
    }

    const handleTouchEnd = (e: TouchEvent) => {
      if (!touchStart.current) return

      if (e.changedTouches.length === 1 && touchStart.current.x !== undefined) {
        const dx = e.changedTouches[0].clientX - touchStart.current.x
        const dy = e.changedTouches[0].clientY - touchStart.current.y

        if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > SWIPE_THRESHOLD) {
          if (dx < 0) handlers.onSwipeLeft?.()
          else handlers.onSwipeRight?.()
        }
      }

      touchStart.current = null
    }

    const handleTouchMove = (e: TouchEvent) => {
      if (e.touches.length === 2 && touchStart.current?.distance) {
        const dx = e.touches[0].clientX - e.touches[1].clientX
        const dy = e.touches[0].clientY - e.touches[1].clientY
        const currentDistance = Math.sqrt(dx * dx + dy * dy)
        const scale = currentDistance / touchStart.current.distance

        if (Math.abs(currentDistance - touchStart.current.distance) > PINCH_THRESHOLD) {
          handlers.onPinch?.(scale)
        }
      }
    }

    el.addEventListener('touchstart', handleTouchStart, { passive: true })
    el.addEventListener('touchend', handleTouchEnd, { passive: true })
    el.addEventListener('touchmove', handleTouchMove, { passive: true })

    return () => {
      el.removeEventListener('touchstart', handleTouchStart)
      el.removeEventListener('touchend', handleTouchEnd)
      el.removeEventListener('touchmove', handleTouchMove)
    }
  }, [handlers])

  return ref
}

export function useNetworkStatus() {
  const [isOnline, setIsOnline] = useState(navigator.onLine)

  useEffect(() => {
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  return isOnline
}