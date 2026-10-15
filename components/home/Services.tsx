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

      <div className="mt-24">
        {services.map((s, i) => (
          <article key={s.title} className="border-t border-paper/15">
            <header className="sticky z-10 grid grid-cols-12 items-baseline bg-ink py-5" style={{ top: i * 76 }}>
              <span className="display col-span-3 text-4xl tab:text-6xl">0{i + 1}.</span>
              <h3 className="display col-span-9 text-4xl tab:text-6xl">{s.title}</h3>
            </header>
            <div className="grid grid-cols-12 pb-20">
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
