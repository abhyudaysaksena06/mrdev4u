'use client'
import { Link } from 'next-view-transitions'
import { usePathname } from 'next/navigation'
import { AnimatePresence, motion } from 'motion/react'
import { useEffect, useState } from 'react'
import { site } from '@/lib/site'
import { useStore } from '@/lib/store'
import { LogoMark } from './logo/LogoMark'
import { LocalTime, MotionToggle, Pill, ThemeToggle } from './ui'

export function Nav() {
  const pathname = usePathname()
  const [hidden, setHidden] = useState(false)
  const [menu, setMenu] = useState(false)
  const logo3d = useStore(s => s.logo3d)
  const docked = useStore(s => s.docked)
  const home = pathname === '/'
  // On the home page the 3D logo flies into this slot; the flat mark takes over once it lands.
  const hideMark = home && logo3d && !docked

  useEffect(() => setMenu(false), [pathname])

  // Hide while scrolling down, return on scroll up (Grigoletti pattern).
  // On the home page it stays put until the 3D logo has docked into it.
  useEffect(() => {
    let last = window.scrollY
    const threshold = home ? window.innerHeight * 0.9 : 140
    const onScroll = () => {
      const y = window.scrollY
      if (Math.abs(y - last) < 6) return
      setHidden(y > last && y > threshold)
      last = y
    }
    setHidden(false)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [home])

  const active = (href: string) => pathname === href || pathname.startsWith(href + '/')
  const shown = !hidden || menu

  return (
    <>
      <header
        className="fixed inset-x-0 top-0 z-50 transition-[translate,opacity] duration-500 ease-soft"
        style={{ translate: shown ? '0 0' : '0 -130%' }}
      >
        <nav aria-label="Main" className="flex items-center justify-between gap-4 px-4 py-4 tab:px-8">
          <Link
            href="/"
            aria-label={`${site.alias}, home`}
            data-cursor="Home"
            className={`relative flex items-center rounded-[4px] border bg-paper px-2.5 py-2 transition-[border-color,background-color] duration-300 ${hideMark ? 'border-transparent bg-transparent' : 'border-ink'}`}
          >
            <span id="nav-logo-slot" className="block h-[1.35rem] w-[1.87rem] text-ink">
              <LogoMark
                className={`size-full transition-opacity duration-300 ${hideMark ? 'opacity-0' : ''}`}
                title={site.alias}
              />
            </span>
          </Link>

          <ul className="hidden items-center gap-1.5 tab:flex">
            {site.nav.map(l => (
              <li key={l.href}>
                <Pill href={l.href} active={active(l.href)}>
                  {l.label}
                </Pill>
              </li>
            ))}
          </ul>

          <div className="flex items-center gap-4">
            <LocalTime className="hidden desk:inline" />
            <MotionToggle className="hidden tab:inline-flex" />
            <ThemeToggle className="hidden tab:inline-flex" />
            <span className="hidden tab:inline-flex">
              <Pill href="/contact" variant="solid" active={active('/contact')} cursor="Say hi">
                {"Let's talk"}
              </Pill>
            </span>
            <button
              type="button"
              className="rounded-[4px] border border-ink bg-paper px-3 py-2.5 font-display text-[15px] uppercase leading-none tab:hidden"
              aria-expanded={menu}
              aria-controls="mobile-menu"
              onClick={() => setMenu(m => !m)}
            >
              {menu ? 'Close' : 'Menu'}
            </button>
          </div>
        </nav>
      </header>

      <AnimatePresence>
        {menu && (
          <motion.div
            className="fixed inset-0 z-40 flex items-end bg-black/40 p-3 backdrop-blur-md tab:hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
            onClick={() => setMenu(false)}
          >
            <motion.div
              id="mobile-menu"
              className="w-full rounded-lg border border-ink bg-paper p-5"
              initial={{ y: 40, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 40, opacity: 0 }}
              transition={{ duration: 0.4, ease: [0.12, 0.23, 0.5, 1] }}
              onClick={e => e.stopPropagation()}
            >
              <ul className="flex flex-col">
                {[{ label: 'Home', href: '/' }, ...site.nav].map(l => (
                  <li key={l.href}>
                    <Link
                      href={l.href}
                      className={`display block py-1 text-6xl ${pathname === l.href ? 'text-accent' : 'text-ink'}`}
                    >
                      {l.label}
                    </Link>
                  </li>
                ))}
              </ul>
              <div className="mt-6 flex items-center justify-between border-t border-line pt-4">
                <LocalTime />
                <span className="flex items-center gap-4">
                  <MotionToggle />
                  <ThemeToggle />
                </span>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
