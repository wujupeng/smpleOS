import { useState, useEffect } from 'react'

export type Breakpoint = 'mobile' | 'tablet' | 'desktop'

const BREAKPOINTS = {
  mobile: 768,
  tablet: 1024,
} as const

export function useBreakpoint(): Breakpoint {
  const [breakpoint, setBreakpoint] = useState<Breakpoint>(() => {
    if (typeof window === 'undefined') return 'desktop'
    const w = window.innerWidth
    if (w < BREAKPOINTS.mobile) return 'mobile'
    if (w < BREAKPOINTS.tablet) return 'tablet'
    return 'desktop'
  })

  useEffect(() => {
    const handleResize = () => {
      const w = window.innerWidth
      if (w < BREAKPOINTS.mobile) setBreakpoint('mobile')
      else if (w < BREAKPOINTS.tablet) setBreakpoint('tablet')
      else setBreakpoint('desktop')
    }

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return breakpoint
}

export function useIsMobile(): boolean {
  return useBreakpoint() === 'mobile'
}

export function useIsTablet(): boolean {
  const bp = useBreakpoint()
  return bp === 'mobile' || bp === 'tablet'
}