import type { Metadata } from 'next'
import { site, values } from '@/lib/site'
import { CtaCard } from '@/components/CtaCard'
import { LineReveal, Marquee, Reveal } from '@/components/motion'
import { IntroFade, IntroLines } from '@/components/intro'

export const metadata: Metadata = {
  title: 'About',
  description: `About ${site.name} (${site.alias}), a creative developer.`,
}

const why = [
  {
    title: 'Why',
    text: 'Too many good products hide behind slow, forgettable websites. I like fixing that.',
  },
  {
    title: 'How',
    text: 'Structure and speed first, then motion and 3D only where they make the message clearer or the moment better.',
  },
  {
    title: 'What',
    text: 'Websites and web apps in React and Next.js, with WebGL and motion when the project calls for it.',
  },
]

export default function AboutPage() {
  return (
    <>
      <section className="px-4 pt-36 tab:px-8 tab:pt-44" style={{ ['--intro-base' as string]: '0.05s' }}>
        <div className="grid gap-10 tab:grid-cols-12">
          <div className="flex items-start gap-5 tab:col-span-8">
            <div
              aria-hidden
              className="display grid size-24 shrink-0 place-items-center rounded-md bg-accent text-5xl text-[#111] tab:size-32 tab:text-6xl"
            >
              {site.name.charAt(0)}
            </div>
            <IntroLines lines={["Hey, I'm", site.alias]} className="display text-[17vw] tab:text-[9rem]" />
          </div>
          <IntroFade delay={200} className="space-y-4 self-end text-lg text-body tab:col-span-4">
            <p>
              I&apos;m {site.name}. I build websites and web apps where the details matter: how they load, how they move,
              and how they feel on a cheap phone.
            </p>
            {/* TODO: add a real portrait in place of the initial above, and a line about you outside work. */}
            <p>Outside work: replace this line with something about you.</p>
          </IntroFade>
        </div>
      </section>

      <section aria-label="What drives me" className="px-4 pt-32 tab:px-8">
        <LineReveal lines={['What drives me']} className="display mb-12 text-6xl tab:text-8xl" />
        <div className="grid gap-3 tab:grid-cols-3">
          {why.map((w, i) => (
            <Reveal key={w.title} delay={i * 0.08} className="rounded-lg bg-ink/5 p-6 tab:min-h-72">
              <h3 className="display text-4xl">{w.title}</h3>
              <p className="mt-6 text-body">{w.text}</p>
            </Reveal>
          ))}
        </div>
      </section>

      <section aria-label="Principles" className="px-4 pt-32 tab:px-8">
        <ul className="border-t border-line">
          {values.map(v => (
            <Reveal as="li" key={v.title} className="grid grid-cols-12 gap-4 border-b border-line py-6">
              <span className="col-span-12 text-2xl tab:col-span-4 tab:text-3xl">{v.title}</span>
              <span className="col-span-12 text-lg text-body tab:col-span-6 tab:col-start-6 tab:text-2xl">{v.text}</span>
            </Reveal>
          ))}
        </ul>
      </section>

      <section aria-label="Toolkit" className="pt-24">
        <p className="mb-6 px-4 font-mono text-xs uppercase text-muted tab:px-8">Toolkit</p>
        <Marquee items={site.toolkit} />
      </section>

      <CtaCard />
    </>
  )
}
