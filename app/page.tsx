import { projects } from '@/lib/projects'
import { site } from '@/lib/site'
import { Preloader, IntroFade, IntroLines, IntroWords } from '@/components/intro'
import { HeroCover } from '@/components/home/HeroCover'
import { HeroDoodle } from '@/components/home/HeroDoodle'
import { Services } from '@/components/home/Services'
import { WorkRows } from '@/components/home/WorkRows'
import { AboutGrow } from '@/components/home/AboutGrow'
import { CtaCard } from '@/components/CtaCard'
import { LineReveal, Marquee, Reveal } from '@/components/motion'
import { Magnetic, Pill } from '@/components/ui'
import { preload } from 'react-dom'

export default function Home() {
  // The hero doodle is needed once the preloader ends.
  preload('/doodle.svg', { as: 'image' })
  return (
    <>
      <Preloader />

      <HeroCover>
        <div className="grid min-h-svh grid-cols-12 gap-x-4 px-4 pt-28 pb-8 tab:px-8 tab:pt-32">
          <div className="col-span-12 flex flex-col desk:col-span-7">
            <IntroLines
              lines={['I build websites', 'people play with', 'and remember']}
              className="display text-[11.6vw] tab:text-[10vw] desk:text-[7.4vw]"
            />
            <div className="mt-auto pt-10">
              <IntroWords
                className="max-w-xl text-xl text-body tab:text-2xl desk:text-[1.75rem] desk:leading-[1.2]"
                text={`I'm ${site.name}, aka ${site.alias}: a creative developer making fast, interactive sites with React, Next.js and WebGL.`}
              />
              <IntroFade delay={450} className="mt-8 flex flex-wrap gap-2">
                <Magnetic>
                  <Pill href="/work" variant="solid" size="lg" cursor="Let's go">
                    See my work
                  </Pill>
                </Magnetic>
                <Magnetic>
                  <Pill href="/contact" size="lg">
                    Get in touch
                  </Pill>
                </Magnetic>
              </IntroFade>
            </div>
          </div>
          <div className="col-span-10 col-start-2 order-first mt-2 mb-8 flex flex-col justify-end tab:col-span-8 tab:col-start-3 desk:order-none desk:col-span-5 desk:col-start-auto desk:mb-0">
            <HeroDoodle />
            <IntroFade delay={600} className="mt-4 hidden items-center gap-4 font-display text-sm uppercase desk:flex">
              <span>By {site.alias}</span>
              <span className="h-px flex-1 bg-ink/40" />
            </IntroFade>
          </div>
        </div>
      </HeroCover>

      <Services />

      <section aria-label="Selected work" className="bg-grid relative z-10 bg-paper px-4 pt-32 pb-12 tab:px-8">
        <div className="mb-14 grid gap-6 tab:grid-cols-12">
          <div className="tab:col-span-7">
            <LineReveal lines={['Selected work']} className="display text-7xl tab:text-[8rem]" />
          </div>
          <Reveal className="max-w-sm self-end text-lg text-body tab:col-span-5">
            <p>A few things I have designed and built. Each one has a short case study: the problem, the decisions, the result.</p>
          </Reveal>
        </div>
        <WorkRows projects={projects} />
      </section>

      <div className="bg-grid relative z-10 bg-paper">
        <AboutGrow />
        <section aria-label="Toolkit" className="py-16">
          <p className="mb-6 px-4 font-mono text-xs uppercase text-muted tab:px-8">Toolkit</p>
          <Marquee items={site.toolkit} />
        </section>
        <CtaCard />
      </div>
    </>
  )
}
