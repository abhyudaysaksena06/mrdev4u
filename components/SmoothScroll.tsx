'use client'
import Lenis from 'lenis'
import { useEffect } from 'react'
import { isReduced } from '@/lib/motion-pref'

let instance: Lenis | null = null
export const getLenis = () => instance

// Lenis on desktop only; touch devices and reduced motion keep native scrolling.
// Created imperatively so toggling it never remounts the page.
export function SmoothScroll({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const fine = matchMedia('(pointer: fine)')
    const update = () => {
      const want = !isReduced() && fine.matches
      if (want && !instance) instance = new Lenis({ duration: 1.15, smoothWheel: true, anchors: true, autoRaf: true })
      if (!want && instance) {
        instance.destroy()
        instance = null
      }
    }
    update()
    window.addEventListener('motionchange', update)
    fine.addEventListener('change', update)
    return () => {
      window.removeEventListener('motionchange', update)
      fine.removeEventListener('change', update)
      instance?.destroy()
      instance = null
    }
  }, [])

  return <>{children}</>
}
