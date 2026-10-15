import { LineReveal, Reveal } from '../motion'
import { ServiceStack } from './ServiceStack'

// Dark panel that slides over the pinned hero, with the services as a stack of cards.
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

      <ServiceStack />
    </section>
  )
}
