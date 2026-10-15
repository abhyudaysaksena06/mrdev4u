// Intro pieces driven by CSS (see "Intro timeline" in globals.css), so they start
// at first paint instead of waiting for JavaScript. Server components.
import { site } from '@/lib/site'
import { LOGO_W, PIECES, piecePath } from './logo/geometry'

export function IntroLines({ lines, className }: { lines: string[]; className?: string }) {
  return (
    <h1 className={className} aria-label={lines.join(' ')}>
      {lines.map((line, i) => (
        <span key={i} aria-hidden className="-mb-[0.06em] block overflow-hidden pb-[0.06em]">
          <span className="intro-line block" style={{ ['--i' as string]: i }}>
            {line}
          </span>
        </span>
      ))}
    </h1>
  )
}

export function IntroWords({ text, className, delay = 0 }: { text: string; className?: string; delay?: number }) {
  const words = text.split(' ')
  return (
    <p className={className}>
      {words.map((w, i) => (
        <span
          key={i}
          className="intro-word inline-block"
          style={{ ['--d' as string]: `${delay + Math.round((i / words.length) * 600)}ms` }}
        >
          {w}
          {i < words.length - 1 ? ' ' : ''}
        </span>
      ))}
    </p>
  )
}

export function IntroFade({ children, delay = 0, className }: { children: React.ReactNode; delay?: number; className?: string }) {
  return (
    <div className={`intro-fade ${className ?? ''}`} style={{ ['--d' as string]: `${delay}ms` }}>
      {children}
    </div>
  )
}

// Preloader (about 4 s, pure CSS so it runs before hydration): the doodle walks in from the left,
// pushing the m/ logo into the centre of the screen, gives a little hop, then the curtain lifts.
// Skipped on client-side returns to home (html.no-intro); short and still with reduced motion.
export function Preloader() {
  return (
    <div className="preloader" aria-hidden>
      <div className="absolute inset-0 grid place-items-center">
        <div className="pusher relative">
          {/* the doodle stands just left of the logo, behind it, so his lean reads as pushing */}
          <div className="absolute right-[86%] bottom-[-1.6%] h-[230%] aspect-[984/2169]">
            <div className="push-lean size-full">
              <div className="push-hop size-full">
                <div className="push-walk size-full">
                  <img src="/doodle.svg" alt="" width={984} height={2169} className="size-full" />
                </div>
              </div>
            </div>
          </div>
          <svg viewBox={`-0.02 -0.02 ${LOGO_W + 0.04} 1.04`} className="push-logo relative block w-[min(46vw,320px)] overflow-visible text-ink">
            {PIECES.map(p => (
              <path
                key={p.id}
                d={piecePath(p)}
                fill={p.accent ? 'var(--accent)' : 'currentColor'}
                stroke={p.accent ? 'var(--accent)' : 'currentColor'}
                strokeWidth={0.006}
              />
            ))}
          </svg>
        </div>
      </div>
      <div className="absolute inset-x-4 bottom-4 flex items-end justify-between tab:inset-x-8 tab:bottom-8">
        <span className="counter display text-[22vw] leading-[0.8] tab:text-[12rem]" />
        <span className="font-mono text-xs uppercase text-body">{site.alias} · portfolio</span>
      </div>
    </div>
  )
}
