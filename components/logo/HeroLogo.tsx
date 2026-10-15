'use client'
import dynamic from 'next/dynamic'
import { useEffect, useState } from 'react'
import { setStore, useStore } from '@/lib/store'
import { LogoMark } from './LogoMark'
import { canUse3D } from './LogoMeshes'

const HeroLogo3D = dynamic(() => import('./HeroLogo3D'), { ssr: false })

export const HERO_ANCHOR_ID = 'hero-logo-anchor'

// Marks the intro as finished once the CSS preloader timeline has played.
function useIntroClock() {
  useEffect(() => {
    const root = document.documentElement
    const skip = root.classList.contains('no-intro') || matchMedia('(prefers-reduced-motion: reduce)').matches
    const id = setTimeout(
      () => {
        root.classList.add('no-intro') // client-side visits back to home skip the preloader
        setStore({ introDone: true })
      },
      skip ? 0 : 1900,
    )
    return () => clearTimeout(id)
  }, [])
}

/**
 * The hero's logo box. Shows the flat SVG mark immediately; on capable devices the 3D logo
 * loads on first interaction, turns into place over the same spot, and docks into the nav on scroll.
 */
export function HeroLogo() {
  useIntroClock()
  const introDone = useStore(s => s.introDone)
  const logo3d = useStore(s => s.logo3d)
  const [load, setLoad] = useState(false)

  // The 3D logo is eye candy, not content: load it on the visitor's first interaction
  // (pointer move, touch, scroll or key) after the intro, so it never delays the page.
  useEffect(() => {
    if (!introDone || !canUse3D()) return
    const events = ['pointermove', 'pointerdown', 'touchstart', 'wheel', 'scroll', 'keydown'] as const
    const go = () => {
      events.forEach(e => window.removeEventListener(e, go))
      setLoad(true)
    }
    events.forEach(e => window.addEventListener(e, go, { passive: true, once: true }))
    return () => events.forEach(e => window.removeEventListener(e, go))
  }, [introDone])

  return (
    <>
      <div id={HERO_ANCHOR_ID} className="intro-fade relative aspect-[1.94/1] w-full" style={{ ['--d' as string]: '120ms' }}>
        <LogoMark
          className={`absolute inset-[9%] size-[82%] text-ink transition-opacity duration-500 ${logo3d ? 'opacity-0' : ''}`}
        />
      </div>
      {load && <HeroLogo3D anchorId={HERO_ANCHOR_ID} slotId="nav-logo-slot" />}
    </>
  )
}
