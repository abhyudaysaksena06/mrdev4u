'use client'
import { useEffect, useRef, useState } from 'react'
import { setStore } from '@/lib/store'
import { isReduced } from '@/lib/motion-pref'

// Marks the intro as finished once the CSS preloader timeline has played.
function useIntroClock() {
  useEffect(() => {
    const root = document.documentElement
    // Matches the CSS timeline: full intro ~4 s, reduced ~0.8 s, skipped on client-side returns.
    const wait = root.classList.contains('no-intro') ? 0 : isReduced() ? 800 : 4000
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
// Things he says when clicked, in turn.
const LINES = ["Hi! I'm Abhyuday", 'Yes, I built all of this', 'Scroll down, it gets better', "Got a project? Let's talk"]

/**
 * The hero element: the top half of the doodle (traced from the reference drawing, see
 * scripts/doodle-trace), rising from the bottom edge after the preloader. It first shows as a
 * plain <img> so the page stays light, then the same cached file is inlined so his parts can move:
 * he follows your cursor, and clicking him makes him hop and say something.
 */
export function HeroDoodle() {
  useIntroClock()
  const img = useRef<HTMLImageElement>(null)
  const slot = useRef<HTMLSpanElement>(null)
  const hopper = useRef<HTMLDivElement>(null)
  const count = useRef(0)
  const [svg, setSvg] = useState<SVGSVGElement | null>(null)
  const [said, setSaid] = useState<{ n: number; text: string } | null>(null)
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
        el.setAttribute('class', 'block h-auto w-full overflow-visible')
        el.setAttribute('aria-hidden', 'true')
        slot.current.replaceChildren(el)
        if (img.current) img.current.hidden = true // swap in the same frame: no double figure
        setSvg(el)
      })
      .catch(() => {}) // the <img> stays; he just doesn't move
    return () => {
      alive = false
    }
  }, [])

  // The speech bubble fades out after a moment.
  useEffect(() => {
    if (!said) return
    const id = setTimeout(() => setSaid(null), 2600)
    return () => clearTimeout(id)
  }, [said])

  const hi = () => {
    const n = count.current++
    setSaid({ n, text: LINES[n % LINES.length] })
    if (!isReduced())
      hopper.current?.animate(
        [{ transform: 'none' }, { transform: 'translateY(-7%)', offset: 0.35 }, { transform: 'none', offset: 0.7 }, { transform: 'translateY(-2%)', offset: 0.85 }, { transform: 'none' }],
        { duration: 650, easing: 'cubic-bezier(0.3, 0.7, 0.4, 1)' },
      )
  }

  return (
    <div className="relative flex justify-center">
      {/* Only his top half shows: the box crops the drawing just above the hands and fades out at the bottom. */}
      <button
        type="button"
        onClick={hi}
        aria-label="Say hi to the doodle"
        data-cursor="Say hi"
        className="doodle-bust relative block aspect-[984/1330] h-[30svh] overflow-hidden tab:h-[38svh] desk:h-[min(58svh,40rem)]"
      >
        <div ref={hopper} className="size-full">
          <div className="doodle-rise">
            <img ref={img} src="/doodle.svg" alt={TITLE} width={984} height={2169} className="block h-auto w-full" />
            <span ref={slot} className="contents" />
          </div>
        </div>
      </button>
      <p
        aria-live="polite"
        className={`pointer-events-none absolute top-[2%] left-1/2 -translate-x-[115%] whitespace-nowrap rounded-[4px] border border-ink bg-paper px-3 py-2 font-display text-sm uppercase leading-none transition-[opacity,translate] duration-300 ease-soft tab:text-base ${said ? 'opacity-100' : 'translate-y-2 opacity-0'}`}
      >
        {said?.text}
      </p>
    </div>
  )
}
