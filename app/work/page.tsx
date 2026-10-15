import type { Metadata } from 'next'
import { projects } from '@/lib/projects'
import { WorkRows } from '@/components/home/WorkRows'
import { CtaCard } from '@/components/CtaCard'
import { IntroFade, IntroLines } from '@/components/intro'

export const metadata: Metadata = {
  title: 'Work',
  description: 'Selected projects, each with a short case study.',
}

export default function WorkPage() {
  return (
    <>
      <section className="px-4 pt-36 pb-12 tab:px-8 tab:pt-44" style={{ ['--intro-base' as string]: '0.05s' }}>
        <div className="mb-16 grid gap-6 tab:grid-cols-12">
          <div className="tab:col-span-7">
            <IntroLines lines={['Work']} className="display text-[28vw] tab:text-[16rem]" />
          </div>
          <IntroFade delay={200} className="max-w-sm self-end text-lg text-body tab:col-span-5">
            <p>
              {projects.length} projects. Open one for the problem, the decisions that shaped it, and the result.
            </p>
          </IntroFade>
        </div>
        <WorkRows projects={projects} immediate />
      </section>
      <CtaCard />
    </>
  )
}
