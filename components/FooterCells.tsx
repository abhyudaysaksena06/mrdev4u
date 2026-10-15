'use client'
import { Link } from 'next-view-transitions'
import { usePathname } from 'next/navigation'
import { site } from '@/lib/site'
import { LogoMark } from './logo/LogoMark'
import { RollText } from './ui'

const PAGES = [{ label: 'Home', href: '/' }, ...site.nav]
const top = 'truncate font-mono text-xs uppercase text-body group-hover:text-paper/70'
const LABELS: Record<string, React.ReactNode> = {
  '/work': <span className={top}>Selected projects</span>,
  '/about': (
    <span className={top}>
      {site.role} · {site.name}
    </span>
  ),
  '/contact': <span className={top}>{site.email}</span>,
}
const brand = (
  <span className="flex items-center gap-2 font-display text-lg uppercase group-hover:text-paper">
    <LogoMark className="h-5 w-10" /> {site.handle}
  </span>
)

// Big link cell: the label sits bottom-left; on hover the cell fills with ink from the bottom.
function Cell({ href, title, top }: { href: string; title: string; top: React.ReactNode }) {
  return (
    <div className="group relative flex min-w-0 flex-col justify-between border-r border-line p-3 last:border-r-0 tab:p-6">
      <span
        aria-hidden
        className="pointer-events-none absolute inset-0 origin-bottom scale-y-0 bg-ink transition-transform duration-500 ease-soft group-hover:scale-y-100"
      />
      <div className="relative z-10 hidden min-w-0 items-center gap-3 tab:flex">{top}</div>
      <span aria-hidden className="relative z-10 self-end font-mono text-xs text-muted tab:hidden">↗</span>
      {/* The link's ::after covers the whole cell, so the entire cell is clickable. */}
      <Link
        href={href}
        data-cursor={title}
        className="display mt-auto text-[min(7.5vw,9.5svh)] transition-colors duration-300 group-hover:text-paper after:absolute after:inset-0 after:z-20 after:content-['']"
      >
        <span className="relative z-10">
          <RollText>{title}</RollText>
        </span>
      </Link>
    </div>
  )
}

/**
 * The footer's three big link cells: every page except the one you are on. Pages without a cell of
 * their own (a case study, the 404) drop Home instead, since the logo already leads there.
 * The first cell carries the m/ mark.
 */
export function FooterCells() {
  const pathname = usePathname()
  const current = PAGES.some(p => p.href === pathname) ? pathname : '/'
  const cells = PAGES.filter(p => p.href !== current)
  return (
    <div className="grid h-[clamp(5.5rem,15.5svh,7.5rem)] shrink-0 grid-cols-3 border-y border-line tab:h-[clamp(7rem,19svh,12rem)]">
      {cells.map((p, i) => (
        <Cell key={p.href} href={p.href} title={p.label} top={i === 0 ? brand : LABELS[p.href]} />
      ))}
    </div>
  )
}
