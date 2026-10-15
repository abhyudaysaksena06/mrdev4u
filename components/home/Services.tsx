import { services } from '@/lib/site'
import { LineReveal, Reveal } from '../motion'

// Dark panel that slides over the pinned hero, listing services as three cards.
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

      {/* Three separate cards in normal flow: nothing pins or overlaps, each card rises in on scroll. */}
      <div className="mt-24 space-y-4">
        {services.map((s, i) => (
          <Reveal key={s.title} as="div" y={60}>
            <article className="group rounded-lg border border-paper/15 bg-paper/[0.03] px-5 transition-colors duration-500 hover:border-paper/40 tab:px-8">
              <header className="grid grid-cols-12 items-baseline border-b border-paper/15 py-6">
                <span className="display col-span-3 text-4xl tab:text-6xl">0{i + 1}.</span>
                <h3 className="display col-span-8 text-4xl tab:text-6xl">{s.title}</h3>
                <span
                  aria-hidden
                  className="col-span-1 justify-self-end text-2xl text-paper/60 transition-transform duration-500 ease-soft group-hover:-rotate-45"
                >
                  ↙
                </span>
              </header>
              <div className="grid grid-cols-12 py-8 tab:py-10">
                <div className="col-span-12 tab:col-span-6 tab:col-start-4">
                  <p className="max-w-md text-lg text-paper/70">{s.text}</p>
                  <ul className="mt-8">
                    {s.items.map((it, j) => (
                      <li key={it} className="flex items-baseline gap-4 border-b border-paper/15 py-2.5 last:border-b-0">
                        <span className="font-mono text-xs text-paper/60">0{j + 1}</span>
                        <span className="display text-xl tab:text-2xl">{it}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </article>
          </Reveal>
        ))}
      </div>
    </section>
  )
}
