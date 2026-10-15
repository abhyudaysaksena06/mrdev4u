import { Link } from 'next-view-transitions'
import { site } from '@/lib/site'
import { LogoMark } from './logo/LogoMark'
import { Wordmark } from './Wordmark'
import { RollText } from './ui'

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

const top = 'truncate font-mono text-xs uppercase text-body group-hover:text-paper/70'

/**
 * The footer fills exactly one screen, so the last scroll shows everything at once:
 * link cells, the invitation, the giant wordmark and the credit line.
 */
export function Footer() {
  return (
    <footer className="relative z-10 flex min-h-svh flex-col overflow-hidden bg-paper tab:min-h-[min(100svh,75vw)]">
      {/* Row 1: three big link cells */}
      <div className="grid h-[clamp(5.5rem,15.5svh,7.5rem)] shrink-0 grid-cols-3 border-y border-line tab:h-[clamp(7rem,19svh,12rem)]">
        <Cell
          href="/work"
          title="Work"
          top={
            <span className="flex items-center gap-2 font-display text-lg uppercase group-hover:text-paper">
              <LogoMark className="h-5 w-7" /> {site.handle}
            </span>
          }
        />
        <Cell href="/about" title="About" top={<span className={top}>{site.role} · {site.name}</span>} />
        <Cell href="/contact" title="Contact" top={<span className={top}>{site.email}</span>} />
      </div>

      {/* Row 2: the invitation on the left; links, availability and email on the right */}
      <div className="flex flex-1 flex-col gap-6 px-4 py-[3svh] tab:grid tab:grid-cols-12 tab:gap-6 tab:px-6 tab:py-[3svh]">
        <h2 className="display text-[min(11vw,7svh)] tab:col-span-7 tab:text-[min(7.2vw,14svh)]">
          Let&apos;s build
          <br />
          something
          <br />
          people remember
        </h2>

        <div className="flex flex-1 flex-col gap-5 tab:col-span-5 tab:justify-between">
          <div className="order-last mt-auto tab:order-none tab:mt-0 tab:self-end tab:text-right">
            <p className="mb-2 font-mono text-xs uppercase text-muted tab:mb-3">Follow</p>
            <ul className="flex flex-wrap gap-x-5 gap-y-1.5 tab:flex-col tab:items-end">
              {site.socials.map(s => (
                <li key={s.label}>
                  <a href={s.href} className="text-sm text-body transition-colors hover:text-ink" target="_blank" rel="noreferrer">
                    {s.label} ↗
                  </a>
                </li>
              ))}
            </ul>
          </div>

          <div className="flex flex-col gap-4 tab:items-end tab:gap-6">
            {site.available && (
              <p className="inline-flex items-center gap-2 self-start bg-accent px-2 py-1 font-display text-sm uppercase text-[#111] tab:order-first tab:self-end">
                <span aria-hidden>●</span> Available for new projects
              </p>
            )}
            <a
              href={`mailto:${site.email}`}
              data-cursor="Write"
              className="group -order-1 flex w-full items-center justify-between gap-4 border-b border-ink pb-2 font-mono text-xs uppercase tab:order-none"
            >
              <span className="text-muted">Email</span>
              <span className="flex items-center gap-2">
                {site.email}
                <span className="transition-transform duration-300 group-hover:translate-x-1">→</span>
              </span>
            </a>
          </div>
        </div>
      </div>

      {/* Row 3: the giant wordmark, edge to edge */}
      <Wordmark text={site.wordmark} />

      <div className="flex shrink-0 flex-col gap-1.5 px-4 pt-3 pb-4 font-mono text-[11px] uppercase text-muted tab:flex-row tab:items-center tab:justify-between tab:px-6 tab:pb-5">
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
