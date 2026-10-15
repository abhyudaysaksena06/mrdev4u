import { Link } from 'next-view-transitions'
import { site } from '@/lib/site'
import { LogoToy } from './logo/LogoToy'
import { LocalTime } from './ui'

const col = 'border-t border-line pt-3'
const label = 'mb-3 font-mono text-xs uppercase text-muted'
const link = 'text-sm text-body transition-colors hover:text-ink'

export function Footer() {
  return (
    <footer className="relative z-10 bg-paper px-4 pt-24 pb-6 tab:px-8">
      <div className="grid gap-10 tab:grid-cols-12">
        <div className="tab:col-span-5">
          <LogoToy className="max-w-md" />
        </div>
        <div className="grid grid-cols-2 gap-8 tab:col-span-7 tab:grid-cols-3">
          <div className={col}>
            <p className={label}>Pages</p>
            <ul className="space-y-1.5">
              {[{ label: 'Home', href: '/' }, ...site.nav].map(l => (
                <li key={l.href}>
                  <Link href={l.href} className={link}>
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
          <div className={col}>
            <p className={label}>Elsewhere</p>
            <ul className="space-y-1.5">
              {site.socials.map(s => (
                <li key={s.label}>
                  <a href={s.href} className={link} target="_blank" rel="noreferrer">
                    {s.label} ↗
                  </a>
                </li>
              ))}
            </ul>
          </div>
          <div className={`${col} col-span-2 tab:col-span-1`}>
            <p className={label}>Local time</p>
            <LocalTime />
            <p className={`${label} mt-6`}>Built with</p>
            <p className="text-sm text-body">Next.js, React Three Fiber, Motion and Lenis.</p>
          </div>
        </div>
      </div>
      <div className="mt-16 flex flex-wrap items-center justify-between gap-2 border-t border-line pt-4 font-mono text-xs uppercase text-muted">
        <span>
          © {new Date().getFullYear()} {site.alias}
        </span>
        <a href="#main" className="hover:text-ink">
          Back to top ↑
        </a>
      </div>
    </footer>
  )
}
