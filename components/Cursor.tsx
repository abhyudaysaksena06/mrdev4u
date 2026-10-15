'use client'
import { useEffect, useRef, useState } from 'react'

// 16 px blend-mode square that follows the pointer. Any element with
// data-cursor="LABEL" turns it into a label pill while hovered.
export function Cursor() {
  const dot = useRef<HTMLDivElement>(null)
  const pill = useRef<HTMLDivElement>(null)
  const [label, setLabel] = useState<string | null>(null)
  const [on, setOn] = useState(false)

  useEffect(() => {
    if (!matchMedia('(pointer: fine)').matches) return
    setOn(true)
    const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches
    let x = -100, y = -100, cx = x, cy = y, raf = 0, visible = false

    const move = (e: PointerEvent) => {
      x = e.clientX
      y = e.clientY
      if (!visible) {
        visible = true
        cx = x
        cy = y
        dot.current?.style.setProperty('opacity', '1')
      }
      pick(e.target as Element | null)
    }
    const pick = (el: Element | null) => {
      const target = el?.closest?.('[data-cursor]')
      setLabel(target ? target.getAttribute('data-cursor') : null)
    }
    // Scrolling moves content under a still pointer, so re-check what is underneath.
    const scroll = () => visible && pick(document.elementFromPoint(x, y))
    const leave = () => {
      visible = false
      dot.current?.style.setProperty('opacity', '0')
      setLabel(null)
    }
    const tick = () => {
      const k = reduce ? 1 : 0.22
      cx += (x - cx) * k
      cy += (y - cy) * k
      const t = `translate3d(${cx}px, ${cy}px, 0)`
      if (dot.current) dot.current.style.transform = t
      if (pill.current) pill.current.style.transform = t
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    window.addEventListener('pointermove', move, { passive: true })
    window.addEventListener('scroll', scroll, { passive: true })
    document.documentElement.addEventListener('pointerleave', leave)
    document.documentElement.classList.add('has-cursor')
    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('pointermove', move)
      window.removeEventListener('scroll', scroll)
      document.documentElement.removeEventListener('pointerleave', leave)
      document.documentElement.classList.remove('has-cursor')
    }
  }, [])

  if (!on) return null
  return (
    <>
      <div
        ref={dot}
        aria-hidden
        className="pointer-events-none fixed top-0 left-0 z-[95] opacity-0 mix-blend-difference transition-opacity duration-200"
      >
        <div
          className="size-4 bg-white transition-transform duration-300 ease-soft"
          style={{ transform: `translate(-50%, -50%) scale(${label ? 0 : 1})` }}
        />
      </div>
      <div ref={pill} aria-hidden className="pointer-events-none fixed top-0 left-0 z-[96]">
        <div
          className="font-mono -translate-y-1/2 translate-x-3 rounded bg-ink px-2.5 py-1.5 text-[11px] tracking-wide whitespace-nowrap text-paper uppercase transition-[opacity,scale] duration-300 ease-soft"
          style={{ opacity: label ? 1 : 0, scale: label ? '1' : '0.6' }}
        >
          {label}
        </div>
      </div>
    </>
  )
}
