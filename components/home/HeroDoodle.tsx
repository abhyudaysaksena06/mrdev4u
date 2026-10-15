'use client'
import { useEffect } from 'react'
import { setStore } from '@/lib/store'
import { isReduced } from '@/lib/motion-pref'
import { Doodle } from '../doodle/Doodle'

// Marks the intro as finished once the CSS preloader timeline has played.
function useIntroClock() {
  useEffect(() => {
    const root = document.documentElement
    // Matches the CSS timeline: full intro ~1.9 s, reduced ~0.8 s, skipped on client-side returns.
    const wait = root.classList.contains('no-intro') ? 0 : isReduced() ? 800 : 1900
    const id = setTimeout(() => {
      root.classList.add('no-intro') // navigating back to home inside the site skips the preloader
      setStore({ introDone: true })
    }, wait)
    return () => clearTimeout(id)
  }, [])
}

// The hero element: the doodle, standing on the hero's baseline.
export function HeroDoodle() {
  useIntroClock()
  return (
    <div className="intro-fade flex justify-center" style={{ ['--d' as string]: '120ms' }}>
      <Doodle className="h-[34svh] w-auto text-ink tab:h-[42svh] desk:h-[min(68svh,46rem)]" />
    </div>
  )
}
