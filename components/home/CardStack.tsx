'use client'
import { useEffect, useRef } from 'react'

/**
 * Sticky card stack. Card i pins one header height (--hh) below card i-1, and is made
 * (n-1-i) header heights taller than the tallest card body (--card), so every card's
 * bottom edge lines up. That way the last card stops exactly under the previous header,
 * and at the end of the stack all cards scroll away together instead of the later ones
 * sliding over earlier headers.
 */
export function CardStack({ className, children }: { className?: string; children: React.ReactNode }) {
  const box = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = box.current
    if (!el) return
    const fit = () => {
      const cards = [...el.children] as HTMLElement[]
      // Natural content height of each card (its children), ignoring the min-height we set.
      const tallest = Math.max(...cards.map(c => [...c.children].reduce((h, k) => h + (k as HTMLElement).offsetHeight, 0)))
      el.style.setProperty('--card', `${Math.ceil(tallest)}px`)
    }
    fit()
    const ro = new ResizeObserver(fit)
    ;[...el.children].forEach(c => [...c.children].forEach(k => ro.observe(k)))
    return () => ro.disconnect()
  }, [])

  return (
    <div ref={box} className={className}>
      {children}
    </div>
  )
}
