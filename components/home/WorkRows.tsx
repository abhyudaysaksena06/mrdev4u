'use client'
import { Link } from 'next-view-transitions'
import type { Project } from '@/lib/projects'
import { ProjectCover } from '../ProjectCover'
import { Reveal } from '../motion'
import { IntroFade } from '../intro'

// Project rows: on hover the row fills black, the cover slides in and the cursor says "View case".
// On touch screens each row shows its cover as a card instead.
// `immediate`: rows are above the fold, so reveal them with CSS from first paint instead of on scroll.
export function WorkRows({ projects, immediate = false }: { projects: Project[]; immediate?: boolean }) {
  return (
    <ul className="border-t border-line">
      {projects.map((p, i) => (
        <Row key={p.slug} immediate={immediate} index={i}>
          <Link
            href={`/work/${p.slug}`}
            data-cursor="View case"
            className="group relative grid grid-cols-12 items-center gap-x-4 gap-y-3 border-b border-line px-2 py-5 tab:py-4"
          >
            <span
              aria-hidden
              className="absolute inset-0 origin-bottom scale-y-0 rounded-md bg-ink transition-transform duration-500 ease-soft group-hover:scale-y-100 group-focus-visible:scale-y-100"
            />
            <span className="relative col-span-12 font-mono text-xs uppercase text-body transition-colors duration-300 group-hover:text-paper/70 tab:col-span-3">
              {p.year}, {p.kind}
            </span>
            <span className="relative col-span-12 flex items-center gap-6 tab:col-span-8">
              <span className="display text-5xl transition-colors duration-300 group-hover:text-paper tab:text-6xl desk:text-7xl">
                {p.title}
              </span>
              <span className="pointer-events-none hidden w-36 -translate-x-4 opacity-0 transition-[opacity,translate] duration-500 ease-soft group-hover:translate-x-0 group-hover:opacity-100 tab:block">
                <ProjectCover project={p} className="aspect-[4/3]" />
              </span>
            </span>
            <span className="relative col-span-12 hidden justify-self-end text-2xl transition-[color,translate] duration-300 group-hover:translate-x-[-6px] group-hover:text-paper tab:col-span-1 tab:block">
              ↗
            </span>
            <span className="relative col-span-12 tab:hidden">
              <ProjectCover project={p} className="aspect-[16/10]" morph={false} />
            </span>
          </Link>
        </Row>
      ))}
    </ul>
  )
}

function Row({ children, immediate, index }: { children: React.ReactNode; immediate: boolean; index: number }) {
  if (immediate)
    return (
      <li>
        <IntroFade delay={250 + index * 70}>{children}</IntroFade>
      </li>
    )
  return (
    <Reveal as="li" delay={index * 0.06} y={24}>
      {children}
    </Reveal>
  )
}
