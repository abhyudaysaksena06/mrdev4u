'use client'
import { useEffect } from 'react'
import { setStore } from '@/lib/store'
import { isReduced } from '@/lib/motion-pref'

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

/**
 * The hero element: the top half of the doodle (traced from the reference drawing, see
 * scripts/doodle-trace), shown still. He gets animated again once the 3D model
 * (scripts/doodle-3d) is signed off.
 */
export function HeroDoodle() {
  useIntroClock()
  return (
    <div className="relative flex justify-center">
      {/* Only his top half shows: the box crops the drawing just above the hands and fades out at the bottom. */}
      <div className="doodle-bust relative block aspect-[1520/1730] h-[39svh] overflow-hidden tab:h-[49svh] desk:h-[min(75svh,52rem)]">
        <div className="mx-auto w-[64.74%] pt-[40.65%]">
          <img src="/doodle.svg" alt="Doodle of Abhyuday" width={984} height={2169} className="block h-auto w-full" />
        </div>
      </div>
    </div>
  )
}
