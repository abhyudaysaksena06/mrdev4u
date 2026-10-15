import { Link } from 'next-view-transitions'
import { site } from '@/lib/site'
import { LogoMark } from './logo/LogoMark'
import { LogoToy } from './logo/LogoToy'
import { Wordmark } from './Wordmark'
import { LocalTime, MotionToggle, RollText, ThemeToggle } from './ui'

const label = 'mb-3 font-mono text-xs uppercase text-muted'
const link = 'text-sm text-body transition-colors hover:text-ink'

// Big link cell: the label sits bottom-left; on hover the cell fills with ink from the bottom.
function Cell({ href, title, top }: { href: string; title: string; top: React.ReactNode }) {
  return (
    <div className="group relative flex min-h-44 flex-col justify-between border-b border-line p-4 tab:min-h-56 tab:border-r tab:border-b-0 tab:p-6 last:tab:border-r-0">
      <span
        aria-hidden
        className="pointer-events-none absolute inset-0 origin-bottom scale-y-0 bg-ink transition-transform duration-500 ease-soft group-hover:scale-y-100"
      />
      <div className="relative z-10 flex flex-wrap items-center gap-3">{top}</div>
      {/* The link's ::after covers the whole cell, so the entire cell is clickable. */}
      <Link
        href={href}
        data-cursor={title}
        className="display text-6xl transition-colors duration-300 group-hover:text-paper after:absolute after:inset-0 after:z-20 after:content-[''] tab:text-7xl desk:text-8xl"
      >
        <span className="relative z-10">
          <RollText>{title}</RollText>
        </span>
      </Link>
    </div>
  )
}

export function Footer() {
  return (
    <footer className="relative z-10 overflow-hidden bg-paper">
      {/* Row 1: three big link cells */}
      <div className="grid border-y border-line tab:grid-cols-3">
        <Cell
          href="/work"
          title="Work"
          top={
            <span className="flex items-center gap-2 font-display text-lg uppercase group-hover:text-paper">
              <LogoMark className="h-5 w-7" /> {site.wordmark}
            </span>
          }
        />
        <Cell
          href="/about"
          title="About"
          top={
            <span className="font-mono text-xs uppercase text-body group-hover:text-paper/70">
              {site.role} · {site.name}
            </span>
          }
        />
        <Cell
          href="/contact"
          title="Contact"
          top={
            <span className="font-mono text-xs uppercase text-body group-hover:text-paper/70">
              {site.email}
            </span>
          }
        />
      </div>

      {/* Row 2: invitation, the playable logo, link columns */}
      <div className="grid gap-12 px-4 pt-14 pb-10 tab:grid-cols-12 tab:px-6">
        <div className="tab:col-span-4">
          <h2 className="display text-5xl tab:text-6xl">
            Let&apos;s build
            <br />
            something
            <br />
            people remember
          </h2>
          <a
            href={`mailto:${site.email}`}
            data-cursor="Write"
            className="group mt-8 flex max-w-sm items-center justify-between border-b border-ink pb-2 font-mono text-xs uppercase"
          >
            <span className="text-muted">Email</span>
            <span className="flex items-center gap-2">
              {site.email}
              <span className="transition-transform duration-300 group-hover:translate-x-1">→</span>
            </span>
          </a>
          {site.available && (
            <p className="mt-5 inline-flex items-center gap-2 bg-accent px-2 py-1 font-display text-sm uppercase text-[#111]">
              <span aria-hidden>●</span> Available for new projects
            </p>
          )}
        </div>

        <div className="tab:col-span-3">
          <LogoToy className="mx-auto max-w-[15rem]" />
        </div>

        <div className="grid grid-cols-2 gap-8 tab:col-span-5 tab:grid-cols-3 tab:text-right">
          <div>
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
          <div>
            <p className={label}>Follow</p>
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
          <div className="col-span-2 tab:col-span-1">
            <p className={label}>Settings</p>
            <div className="flex flex-col gap-2 tab:items-end">
              <LocalTime />
              <MotionToggle />
              <ThemeToggle />
            </div>
          </div>
        </div>
      </div>

      {/* Row 3: the giant wordmark, edge to edge */}
      <Wordmark text={site.wordmark} />

      <div className="flex flex-wrap items-center justify-between gap-3 px-4 pt-3 pb-5 font-mono text-[11px] uppercase text-muted tab:px-6">
        <span className="flex items-center gap-2">
          <LogoMark className="h-3.5 w-5 text-ink" />
          Designed and built by {site.name}
        </span>
        <span className="flex items-center gap-5">
          <span>
            © {new Date().getFullYear()} {site.wordmark}
          </span>
          <a href="#main" className="hover:text-ink">
            Back to top ↑
          </a>
        </span>
      </div>
    </footer>
  )
}
