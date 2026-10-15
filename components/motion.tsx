'use client'
import { motion, type Variants } from 'motion/react'
import { useReduced } from '@/lib/motion-pref'

export const EASE = [0.12, 0.23, 0.5, 1] as const

// Fade + rise when 20% in view, once.
export function Reveal({
  children,
  delay = 0,
  y = 40,
  className,
  as = 'div',
}: {
  children: React.ReactNode
  delay?: number
  y?: number
  className?: string
  as?: 'div' | 'li' | 'section' | 'p'
}) {
  const reduce = useReduced()
  const M = motion[as]
  return (
    <M
      className={className}
      initial={{ opacity: 0, y: reduce ? 0 : y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.2 }}
      transition={{ duration: reduce ? 0.2 : 0.5, ease: EASE, delay: reduce ? 0 : delay }}
    >
      {children}
    </M>
  )
}

// Each line rises out of a mask when the heading scrolls into view.
// The in-view trigger sits on the heading itself: the masked lines start clipped,
// so observing them directly would never fire.
export function LineReveal({ lines, className, as = 'h2' }: { lines: string[]; className?: string; as?: 'h1' | 'h2' }) {
  const reduce = useReduced()
  const Tag = as === 'h1' ? motion.h1 : motion.h2
  const variants: Variants = {
    hidden: { y: reduce ? 0 : '105%', opacity: reduce ? 0 : 1 },
    shown: (i: number) => ({
      y: 0,
      opacity: 1,
      transition: { duration: reduce ? 0.2 : 0.6, ease: EASE, delay: reduce ? 0 : i * 0.07 },
    }),
  }
  return (
    <Tag
      className={className}
      aria-label={lines.join(' ')}
      initial="hidden"
      whileInView="shown"
      viewport={{ once: true, amount: 0.3 }}
    >
      {lines.map((line, i) => (
        <span key={i} aria-hidden className="-mb-[0.06em] block overflow-hidden pb-[0.06em]">
          <motion.span className="block" custom={i} variants={variants}>
            {line}
          </motion.span>
        </span>
      ))}
    </Tag>
  )
}

export function Marquee({ items, duration = 40, className = '' }: { items: readonly string[]; duration?: number; className?: string }) {
  const row = (hidden: boolean) => (
    <ul className="flex shrink-0 items-center" aria-hidden={hidden || undefined}>
      {items.map(t => (
        <li key={t} className="flex items-center">
          <span className="display px-6 text-5xl tab:text-7xl">{t}</span>
          <span className="size-2.5 rounded-full bg-accent" aria-hidden />
        </li>
      ))}
    </ul>
  )
  return (
    <div className={`overflow-hidden ${className}`}>
      <div className="marquee flex w-max" style={{ ['--marquee-duration' as string]: `${duration}s` }}>
        {row(false)}
        {row(true)}
      </div>
    </div>
  )
}
