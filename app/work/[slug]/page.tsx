import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { Link } from 'next-view-transitions'
import { getProject, projects } from '@/lib/projects'
import { ProjectCover } from '@/components/ProjectCover'
import { CtaCard } from '@/components/CtaCard'
import { LineReveal, Reveal } from '@/components/motion'
import { Pill } from '@/components/ui'

type Params = { params: Promise<{ slug: string }> }

export function generateStaticParams() {
  return projects.map(p => ({ slug: p.slug }))
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const project = getProject((await params).slug)
  return project ? { title: project.title, description: project.summary } : {}
}

export default async function CaseStudy({ params }: Params) {
  const project = getProject((await params).slug)
  if (!project) notFound()
  const i = projects.indexOf(project)
  const next = projects[(i + 1) % projects.length]

  return (
    <>
      <article className="px-4 pt-28 tab:px-8 tab:pt-32">
        <ProjectCover project={project} size="lg" className="aspect-[4/5] tab:aspect-[16/8]" />

        <dl className="mt-6 grid grid-cols-2 gap-y-6 border-b border-line pb-6 tab:grid-cols-4">
          {[
            ['Role', project.role],
            ['Year', String(project.year)],
            ['Type', project.kind],
            ['Stack', project.stack.join(', ')],
          ].map(([k, v]) => (
            <div key={k}>
              <dt className="font-mono text-xs uppercase text-muted">{k}</dt>
              <dd className="mt-1 text-body">{v}</dd>
            </div>
          ))}
        </dl>

        <div className="grid gap-x-4 gap-y-16 py-24 tab:grid-cols-12">
          <div className="tab:col-span-4">
            <LineReveal as="h1" lines={[project.title]} className="display text-6xl tab:text-7xl" />
            {project.link && (
              <div className="mt-8">
                <Pill href={project.link} cursor="Open">
                  Visit project
                </Pill>
              </div>
            )}
          </div>
          <div className="space-y-16 tab:col-span-7 tab:col-start-6">
            <Reveal>
              <p className="text-2xl leading-snug tab:text-3xl">{project.summary}</p>
            </Reveal>
            <Reveal>
              <h2 className="mb-3 font-mono text-xs uppercase text-muted">The problem</h2>
              <p className="text-lg text-body">{project.problem}</p>
            </Reveal>
            <div>
              <h2 className="mb-3 font-mono text-xs uppercase text-muted">Key decisions</h2>
              <ol className="border-t border-line">
                {project.decisions.map((d, n) => (
                  <Reveal as="li" key={d.title} className="grid grid-cols-12 gap-4 border-b border-line py-6">
                    <span className="col-span-2 font-mono text-xs text-muted">0{n + 1}</span>
                    <div className="col-span-10">
                      <h3 className="display text-3xl">{d.title}</h3>
                      <p className="mt-2 text-body">{d.text}</p>
                    </div>
                  </Reveal>
                ))}
              </ol>
            </div>
            <Reveal>
              <h2 className="mb-3 font-mono text-xs uppercase text-muted">The result</h2>
              <p className="text-lg text-body">{project.result}</p>
            </Reveal>
          </div>
        </div>

        <Link
          href={`/work/${next.slug}`}
          data-cursor="Next"
          className="group block border-t border-line py-10"
        >
          <span className="font-mono text-xs uppercase text-muted">Next project</span>
          <span className="display mt-2 block text-[15vw] transition-colors group-hover:text-accent tab:text-[9rem]">
            {next.title} →
          </span>
        </Link>
      </article>
      <CtaCard />
    </>
  )
}
