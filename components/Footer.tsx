import { site } from '@/lib/site'
import { LogoMark } from './logo/LogoMark'
import { FooterCells } from './FooterCells'
import { Wordmark } from './Wordmark'

/**
 * The footer fills exactly one screen, so the last scroll shows everything at once:
 * link cells, the invitation, the giant wordmark and the credit line.
 */
export function Footer() {
  return (
    <footer className="bg-grid relative z-10 flex min-h-svh flex-col overflow-hidden bg-paper tab:min-h-[min(100svh,75vw)]">
      {/* Row 1: three big link cells, for every page but this one */}
      <FooterCells />

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
            <p className="mb-2 font-mono text-xs uppercase text-muted tab:mb-3 tab:text-sm">Follow</p>
            <ul className="flex flex-wrap gap-x-5 gap-y-1 tab:flex-col tab:items-end tab:gap-y-0">
              {site.socials.map(s => (
                <li key={s.label}>
                  <a href={s.href} className="display group/s inline-flex items-center gap-1.5 text-[min(6vw,4.5svh)] text-body transition-colors hover:text-accent tab:text-[min(3.4vw,6svh)]" target="_blank" rel="noreferrer">
                    {s.label}
                    <span aria-hidden className="text-[0.6em] transition-transform duration-300 group-hover/s:-translate-y-1 group-hover/s:translate-x-1">↗</span>
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
          <LogoMark className="h-3.5 w-7 text-ink" />
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
