'use client'
import { Link } from 'next-view-transitions'
import { motion, useMotionValue, useSpring, useReducedMotion } from 'motion/react'
import { useEffect, useState } from 'react'
import { site } from '@/lib/site'

// Label that rolls up to a second copy on hover (the copy is hidden from screen readers).
export function RollText({ children, hoverClass = '' }: { children: string; hoverClass?: string }) {
  return (
    <span className="roll">
      <span>{children}</span>
      <span aria-hidden className={hoverClass}>
        {children}
      </span>
    </span>
  )
}

const pillBase =
  'group relative inline-flex items-center overflow-hidden rounded-[4px] border font-display uppercase leading-none transition-colors'

// Grigoletti-style pill: a dark fill pops from the centre while the label rolls to a light copy.
export function Pill({
  href,
  children,
  active = false,
  size = 'md',
  variant = 'outline',
  cursor,
  onClick,
}: {
  href: string
  children: string
  active?: boolean
  size?: 'md' | 'lg'
  variant?: 'outline' | 'solid'
  cursor?: string
  onClick?: () => void
}) {
  const pad = size === 'lg' ? 'px-5 py-3.5 text-lg' : 'px-3 py-2.5 text-[15px]'
  const tone = active
    ? 'border-accent bg-accent text-[#111]'
    : variant === 'solid'
      ? 'border-ink bg-ink text-paper'
      : 'border-ink bg-paper text-ink'
  const fill = variant === 'solid' && !active ? 'bg-accent' : 'bg-ink'
  const hoverText = variant === 'solid' && !active ? 'text-[#111]' : 'text-paper'
  const external = href.startsWith('http') || href.startsWith('mailto:')
  const inner = (
    <>
      <span
        aria-hidden
        className={`absolute inset-0 scale-0 rounded-[3px] ${fill} transition-transform duration-500 ease-[cubic-bezier(.34,1.3,.64,1)] group-hover:scale-100 group-focus-visible:scale-100`}
      />
      <span className="relative">
        <RollText hoverClass={hoverText}>{children}</RollText>
      </span>
    </>
  )
  const cls = `${pillBase} ${pad} ${tone}`
  if (external)
    return (
      <a href={href} className={cls} data-cursor={cursor} target={href.startsWith('http') ? '_blank' : undefined} rel="noreferrer">
        {inner}
      </a>
    )
  return (
    <Link href={href} className={cls} data-cursor={cursor} aria-current={active ? 'page' : undefined} onClick={onClick}>
      {inner}
    </Link>
  )
}

// Wraps anything in a gentle magnetic pull toward the pointer (fine pointers only).
export function Magnetic({ children, strength = 0.18 }: { children: React.ReactNode; strength?: number }) {
  const reduce = useReducedMotion()
  const x = useMotionValue(0)
  const y = useMotionValue(0)
  const spring = { stiffness: 500, damping: 60, mass: 1 }
  const sx = useSpring(x, spring)
  const sy = useSpring(y, spring)
  if (reduce) return <span className="inline-block">{children}</span>
  return (
    <motion.span
      className="inline-block"
      style={{ x: sx, y: sy }}
      onPointerMove={e => {
        if (e.pointerType !== 'mouse') return
        const r = e.currentTarget.getBoundingClientRect()
        x.set((e.clientX - r.left - r.width / 2) * strength)
        y.set((e.clientY - r.top - r.height / 2) * strength)
      }}
      onPointerLeave={() => {
        x.set(0)
        y.set(0)
      }}
    >
      {children}
    </motion.span>
  )
}

export function LocalTime({ className = '' }: { className?: string }) {
  const [now, setNow] = useState<string | null>(null)
  useEffect(() => {
    const fmt = new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: site.timeZone, timeZoneName: site.city ? undefined : 'short' })
    const tick = () => setNow(fmt.format(new Date()))
    tick()
    const id = setInterval(tick, 15_000)
    return () => clearInterval(id)
  }, [])
  return (
    <span className={`font-mono text-xs uppercase tracking-tight text-body ${className}`}>
      {site.city && <span>{site.city} </span>}
      <span className="tabular-nums">{now ?? '--:--'}</span>
      {site.available && (
        <>
          {' · '}
          <span className="inline-flex items-center gap-1.5">
            <span className="size-1.5 rounded-full bg-accent" aria-hidden />
            available
          </span>
        </>
      )}
    </span>
  )
}

export function ThemeToggle({ className = '' }: { className?: string }) {
  const [theme, setTheme] = useState<'light' | 'dark' | null>(null)
  useEffect(() => {
    setTheme(document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light')
  }, [])
  const toggle = () => {
    const next = theme === 'dark' ? 'light' : 'dark'
    document.documentElement.dataset.theme = next
    try {
      localStorage.setItem('theme', next)
    } catch {}
    setTheme(next)
    window.dispatchEvent(new Event('themechange'))
  }
  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={`${theme ?? 'light'} theme, switch to ${theme === 'dark' ? 'light' : 'dark'}`}
      data-cursor={theme === 'dark' ? 'Light' : 'Dark'}
      className={`group inline-flex items-center gap-2 font-mono text-xs uppercase text-body hover:text-ink ${className}`}
    >
      <span className="relative size-3 overflow-hidden rounded-[2px] border border-current">
        <span className="absolute inset-y-0 left-0 w-1/2 bg-current" />
      </span>
      <span suppressHydrationWarning>{theme ?? 'theme'}</span>
    </button>
  )
}
