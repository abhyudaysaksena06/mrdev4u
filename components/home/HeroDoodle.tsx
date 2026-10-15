'use client'
import { useEffect, useRef, useState } from 'react'
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

const clamp = (v: number, a = -1, b = 1) => Math.min(b, Math.max(a, v))
const IDLE_AFTER = 6000 // ms without pointer movement before he starts looking around on his own

/**
 * Makes the doodle look at the cursor: the pupils follow it, the head turns toward it and tilts,
 * and he sways a little. Without a mouse (or after a while without movement) he looks around
 * slowly. Runs only while the hero is on screen and stays still when motion is reduced.
 */
function useLookAt(svg: SVGSVGElement | null) {
  useEffect(() => {
    if (!svg) return
    const q = (name: string) => svg.querySelector<SVGGElement>(`[data-part="${name}"]`)!
    const parts = { upper: q('upper'), head: q('head'), pupils: q('pupils') }
    const fine = matchMedia('(hover: hover) and (pointer: fine)').matches

    const target = { x: 0, y: 0 }
    const cur = { x: 0, y: 0 }
    let pointer: { x: number; y: number } | null = null
    let lastMove = -Infinity
    let raf = 0
    let last = 0
    let visible = true

    // Units are the traced artwork's (about 3 per original pixel). Pivots: head 498 549, feet 492 2110.
    const apply = (t: number) => {
      const { x, y } = cur
      const breathe = Math.sin(t / 650) * 3
      parts.upper.setAttribute('transform', `translate(0 ${breathe.toFixed(2)}) rotate(${(x * 0.8).toFixed(3)} 492 2110)`)
      parts.head.setAttribute('transform', `translate(${(x * 3).toFixed(2)} ${(y * 3).toFixed(2)}) rotate(${(x * 3).toFixed(3)} 498 549)`)
      parts.pupils.setAttribute('transform', `translate(${(x * 11).toFixed(2)} ${(y * 7).toFixed(2)})`)
    }

    const tick = (t: number) => {
      raf = 0
      const dt = Math.min(0.05, (t - (last || t)) / 1000)
      last = t
      if (pointer && t - lastMove < IDLE_AFTER) {
        // Aim from the middle of his face toward the cursor.
        const r = parts.head.getBoundingClientRect()
        target.x = clamp((pointer.x - (r.left + r.width / 2)) / (innerWidth * 0.45))
        target.y = clamp((pointer.y - (r.top + r.height * 0.55)) / (innerHeight * 0.45))
      } else {
        // Idle: a slow, easy look around.
        target.x = Math.sin(t / 2300) * 0.55 + Math.sin(t / 900) * 0.08
        target.y = Math.sin(t / 3100) * 0.25 - 0.05
      }
      const k = 1 - Math.exp(-dt * 7)
      cur.x += (target.x - cur.x) * k
      cur.y += (target.y - cur.y) * k
      apply(t)
      if (visible) raf = requestAnimationFrame(tick)
    }
    const start = () => {
      if (!raf && visible && !isReduced()) raf = requestAnimationFrame(tick)
    }
    const stop = () => {
      cancelAnimationFrame(raf)
      raf = 0
      last = 0
    }

    const onMove = (e: PointerEvent) => {
      if (e.pointerType !== 'mouse' && e.pointerType !== 'pen') return
      pointer = { x: e.clientX, y: e.clientY }
      lastMove = performance.now()
    }
    const onLeave = () => (pointer = null)
    const onMotion = () => {
      if (isReduced()) {
        stop()
        cur.x = cur.y = 0
        apply(0)
      } else start()
    }
    const io = new IntersectionObserver(([e]) => {
      visible = e.isIntersecting && !document.hidden
      if (visible) start()
      else stop()
    })
    io.observe(svg)
    const onVis = () => {
      visible = !document.hidden
      if (visible) start()
      else stop()
    }

    if (fine) window.addEventListener('pointermove', onMove, { passive: true })
    document.documentElement.addEventListener('mouseleave', onLeave)
    window.addEventListener('motionchange', onMotion)
    document.addEventListener('visibilitychange', onVis)
    start()
    return () => {
      stop()
      io.disconnect()
      window.removeEventListener('pointermove', onMove)
      document.documentElement.removeEventListener('mouseleave', onLeave)
      window.removeEventListener('motionchange', onMotion)
      document.removeEventListener('visibilitychange', onVis)
    }
  }, [svg])
}

const TITLE = 'Doodle of Abhyuday'
const SIZE = 'h-[34svh] w-auto tab:h-[42svh] desk:h-[min(68svh,46rem)]'

/**
 * The hero element: the doodle, traced from the reference drawing (scripts/doodle-trace).
 * It first shows as a plain <img> so the page stays light, then the same file (now cached) is
 * inlined so its parts can move and he keeps an eye on your cursor.
 */
export function HeroDoodle() {
  useIntroClock()
  const img = useRef<HTMLImageElement>(null)
  const slot = useRef<HTMLSpanElement>(null)
  const [svg, setSvg] = useState<SVGSVGElement | null>(null)
  useLookAt(svg)

  useEffect(() => {
    let alive = true
    fetch('/doodle.svg')
      .then(r => r.text())
      .then(text => {
        if (!alive || !slot.current) return
        const parsed = new DOMParser().parseFromString(text, 'image/svg+xml').documentElement
        if (parsed.nodeName !== 'svg') return
        const el = document.importNode(parsed, true) as unknown as SVGSVGElement
        el.setAttribute('class', `${SIZE} overflow-visible`)
        el.setAttribute('role', 'img')
        el.setAttribute('aria-label', TITLE)
        slot.current.replaceChildren(el)
        if (img.current) img.current.hidden = true // swap in the same frame: no double figure
        setSvg(el)
      })
      .catch(() => {}) // the <img> stays; he just doesn't move
    return () => {
      alive = false
    }
  }, [])

  return (
    <div className="intro-fade flex justify-center" style={{ ['--d' as string]: '120ms' }}>
      <img ref={img} src="/doodle.svg" alt={TITLE} width={984} height={2169} className={SIZE} />
      <span ref={slot} className="contents" />
    </div>
  )
}
