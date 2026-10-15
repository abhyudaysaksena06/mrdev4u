// Intro pieces driven by CSS (see "Intro timeline" in globals.css), so they start
// at first paint instead of waiting for JavaScript. Server components.
import { site } from '@/lib/site'

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

// Preloader (about 4 s): a short animated "film" in which the doodle pushes the m/ logo in from the
// right until it sits in the centre, then hops. The film is a self-contained animated SVG
// (public/preloader, built by scripts/doodle-trace), so it runs before any JavaScript; CSS picks the
// wide or tall cut and the light or dark version. Skipped on client-side returns to home
// (html.no-intro); short with reduced motion.
export function Preloader() {
  return (
    <div className="preloader" aria-hidden>
      <div className="preloader-film absolute inset-0" />
      <div className="absolute inset-x-4 bottom-4 flex items-end justify-between tab:inset-x-8 tab:bottom-8">
        <span className="counter display text-[22vw] leading-[0.8] tab:text-[12rem]" />
        <span className="font-mono text-xs uppercase text-body">{site.alias} · portfolio</span>
      </div>
    </div>
  )
}
