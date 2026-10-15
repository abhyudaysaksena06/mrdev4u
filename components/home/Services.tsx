import { services } from '@/lib/site'
import { LineReveal, Reveal } from '../motion'

// Dark panel that slides over the pinned hero. Service headers stick and stack as you scroll.
export function Services() {
  return (
    <section
      aria-label="What I do"
      className="relative z-10 rounded-t-lg bg-ink px-4 pt-28 pb-24 text-paper tab:px-8 tab:pt-40"
    >
      <div className="grid gap-8 tab:grid-cols-12">
        <div className="tab:col-span-7">
          <LineReveal lines={['What I do']} className="display text-7xl tab:text-[8rem]" />
        </div>
        <Reveal className="max-w-md self-end text-lg text-paper/70 tab:col-span-5">
          <p>
            I design and build websites that feel fast and alive: clear structure first, then motion and 3D where it
            earns its place.
          </p>
        </Reveal>
      </div>

      {/* Stacking cards: each card pins below the previous card's header row and covers its body,
          so text never scrolls half-hidden under a sticky header. */}
      {/* --hh is the header height; each card pins exactly one header below the previous one,
          so stacked headers line up edge to edge with nothing peeking between them. */}
      <div className="mt-24 [--hh:76px] tab:[--hh:104px]">
        {services.map((s, i) => (
          <article
            key={s.title}
            className="sticky min-h-[78svh] border-t border-paper/15 bg-ink"
            style={{ top: `calc(16px + ${i} * var(--hh))`, zIndex: i + 1 }}
          >
            <header className="grid h-[var(--hh)] grid-cols-12 items-center">
              <span className="display col-span-3 text-4xl tab:text-6xl">0{i + 1}.</span>
              <h3 className="display col-span-8 text-4xl tab:text-6xl">{s.title}</h3>
              <span aria-hidden className="col-span-1 justify-self-end text-2xl text-paper/60">
                ↙
              </span>
            </header>
            <div className="grid grid-cols-12 pt-4 pb-20">
              <div className="col-span-12 tab:col-span-6 tab:col-start-4">
                <p className="max-w-md text-lg text-paper/70">{s.text}</p>
                <ul className="mt-8">
                  {s.items.map((it, j) => (
                    <li key={it} className="flex items-baseline gap-4 border-b border-paper/15 py-2.5">
                      <span className="font-mono text-xs text-paper/60">0{j + 1}</span>
                      <span className="display text-xl tab:text-2xl">{it}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}
