'use client'
import { useCallback, useEffect, useRef, useState } from 'react'
import { setStore } from '@/lib/store'
import { isReduced } from '@/lib/motion-pref'
import { MOVES, ROTATION, rest, sample, type Channel, type Move } from './doodleMoves'

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
const FEET = '492 2110' // pivot for whole-body moves, in the drawing's units
const f = (v: number) => v.toFixed(2)
const neg = (pt: string) => pt.split(' ').map(v => -Number(v)).join(' ')

type Playing = { move: Move; start: number } | null

/**
 * Brings the doodle to life: he looks at the cursor (pupils, head turn and tilt, a little sway),
 * breathes, and plays a move when asked (see doodleMoves.ts). Without a mouse, or after a while
 * without movement, he looks around slowly. Runs only while the hero is on screen; still when motion
 * is reduced. Returns play(name).
 */
function useDoodle(svg: SVGSVGElement | null) {
  const playing = useRef<Playing>(null)
  const kick = useRef<() => void>(() => {})

  useEffect(() => {
    if (!svg) return
    const q = (name: string) => svg.querySelector<SVGGElement>(`[data-part="${name}"]`)
    const upper = q('upper')!
    // wrap everything but the shadow so whole-body moves (jump, spin) can scale about the feet
    const body = document.createElementNS('http://www.w3.org/2000/svg', 'g')
    upper.parentNode!.insertBefore(body, upper)
    body.appendChild(upper)
    const parts = { upper, head: q('head')!, pupils: q('pupils')!, armL: q('arm-l'), foreL: q('fore-l'), armR: q('arm-r'), foreR: q('fore-r') }
    const shadow = svg.querySelector<SVGEllipseElement>('.doodle-shadow')
    const pivot = (el: SVGGElement | null) => el?.getAttribute('data-pivot') ?? '0 0'
    const pb = parts.pupils.getBBox()
    const pupilC = `${f(pb.x + pb.width / 2)} ${f(pb.y + pb.height / 2)}`
    const shadowC = shadow ? `${shadow.getAttribute('cx')} ${shadow.getAttribute('cy')}` : '0 0'
    const fine = matchMedia('(hover: hover) and (pointer: fine)').matches

    const target = { x: 0, y: 0 }
    const cur = { x: 0, y: 0 }
    let pointer: { x: number; y: number } | null = null
    let lastMove = -Infinity
    let raf = 0
    let last = 0
    let visible = true

    const apply = (t: number) => {
      let m = {} as Record<Channel, number>
      const p = playing.current
      if (p) {
        const prog = (t - p.start) / (p.move.duration * 1000)
        if (prog >= 1) playing.current = null
        else m = sample(p.move, Math.max(0, prog))
      }
      const c = (k: Channel) => m[k] ?? rest(k)
      const { x, y } = cur
      const breathe = Math.sin(t / 650) * 3
      body.setAttribute('transform', `translate(${f(c('bodyX'))} ${f(c('bodyY'))}) rotate(${f(c('bodyR'))} ${FEET}) translate(${FEET}) scale(${f(c('bodySX'))} ${f(c('bodySY'))}) translate(${neg(FEET)})`)
      parts.upper.setAttribute('transform', `translate(0 ${f(breathe + c('upperY'))}) rotate(${f(x * 0.8 + c('upperR'))} ${FEET})`)
      parts.head.setAttribute('transform', `translate(${f(x * 3 + c('headX'))} ${f(y * 3 + c('headY'))}) rotate(${f(x * 3 + c('headR'))} 498 549)`)
      parts.pupils.setAttribute('transform', `translate(${f(x * 11 + c('pupilsX'))} ${f(y * 7 + c('pupilsY'))}) translate(${pupilC}) scale(${f(c('pupilsS'))}) translate(${neg(pupilC)})`)
      parts.armL?.setAttribute('transform', `rotate(${f(c('armL'))} ${pivot(parts.armL)})`)
      parts.foreL?.setAttribute('transform', `rotate(${f(c('foreL'))} ${pivot(parts.foreL)})`)
      parts.armR?.setAttribute('transform', `rotate(${f(c('armR'))} ${pivot(parts.armR)})`)
      parts.foreR?.setAttribute('transform', `rotate(${f(c('foreR'))} ${pivot(parts.foreR)})`)
      shadow?.setAttribute('transform', `translate(${shadowC}) scale(${f(c('shadowS'))} 1) translate(${neg(shadowC)})`)
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
    kick.current = start

    const onMove = (e: PointerEvent) => {
      if (e.pointerType !== 'mouse' && e.pointerType !== 'pen') return
      pointer = { x: e.clientX, y: e.clientY }
      lastMove = performance.now()
    }
    const onLeave = () => (pointer = null)
    const onMotion = () => {
      if (isReduced()) {
        stop()
        playing.current = null
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

  return useCallback((name: string) => {
    const move = MOVES[name]
    if (!move || isReduced()) return
    playing.current = { move, start: performance.now() }
    kick.current()
  }, [])
}

const TITLE = 'Doodle of Abhyuday'

/**
 * The hero element: the top half of the doodle (traced from the reference drawing, see
 * scripts/doodle-trace), rising from the bottom edge after the preloader. It first shows as a plain
 * <img> so the page stays light, then the same cached file is inlined so his parts can move: he
 * follows your cursor, and every click plays a different move with a line to go with it.
 */
export function HeroDoodle() {
  useIntroClock()
  const img = useRef<HTMLImageElement>(null)
  const slot = useRef<HTMLSpanElement>(null)
  const next = useRef(0)
  const lastMove = useRef('')
  const clicks = useRef<number[]>([])
  const [svg, setSvg] = useState<SVGSVGElement | null>(null)
  const [said, setSaid] = useState<{ n: number; text: string } | null>(null)
  const play = useDoodle(svg)

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
    const id = setTimeout(() => setSaid(null), 2400)
    return () => clearTimeout(id)
  }, [said])

  const hi = () => {
    const now = performance.now()
    clicks.current = [...clicks.current.filter(t => now - t < 1600), now]
    let name: string
    if (clicks.current.length >= 5) {
      name = 'startled' // rapid clicking startles him
      clicks.current = []
    } else {
      name = ROTATION[next.current % ROTATION.length]
      if (name === lastMove.current) name = ROTATION[++next.current % ROTATION.length]
      next.current++
    }
    lastMove.current = name
    setSaid(s => ({ n: (s?.n ?? 0) + 1, text: MOVES[name].line ?? '' }))
    play(name)
  }

  return (
    <div className="relative flex justify-center">
      {/* Only his top half shows: the box crops the drawing just above the hands and fades out at the
          bottom. Room above and at the sides leaves space for jumps, waves and flung arms. */}
      <button
        type="button"
        onClick={hi}
        aria-label="Say hi to the doodle"
        data-cursor="Say hi"
        className="doodle-bust relative block aspect-[1520/1730] h-[39svh] overflow-hidden tab:h-[49svh] desk:h-[min(75svh,52rem)]"
      >
        {/* side room (the drawing is 984 wide in a 1520-wide box) for arms flung out */}
        <div className="doodle-rise mx-auto w-[64.74%] pt-[40.65%]">
          <img ref={img} src="/doodle.svg" alt={TITLE} width={984} height={2169} className="block h-auto w-full" />
          <span ref={slot} className="contents" />
        </div>
      </button>
      <p
        aria-live="polite"
        className={`pointer-events-none absolute top-[17%] left-1/2 -translate-x-[115%] whitespace-nowrap rounded-[4px] border border-ink bg-paper px-3 py-2 font-display text-sm uppercase leading-none transition-[opacity,translate] duration-300 ease-soft tab:text-base ${said ? 'opacity-100' : 'translate-y-2 opacity-0'}`}
      >
        {said?.text}
      </p>
    </div>
  )
}
