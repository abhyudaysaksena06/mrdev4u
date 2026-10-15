import type { Project } from '@/lib/projects'

// Generated cover for a project (no image needed). Shares a view-transition name
// with the case-study hero so it morphs between pages.
export function ProjectCover({
  project,
  size = 'sm',
  className = '',
  morph = true,
}: {
  project: Project
  size?: 'sm' | 'lg'
  className?: string
  morph?: boolean
}) {
  const big = size === 'lg'
  return (
    <div
      className={`relative flex flex-col justify-between overflow-hidden rounded-lg ring-1 ring-white/15 ${big ? 'p-6 tab:p-10' : 'p-3'} ${className}`}
      style={{ background: project.color, color: project.ink, viewTransitionName: morph ? `cover-${project.slug}` : undefined }}
    >
      <div className={`flex justify-between font-mono uppercase ${big ? 'text-xs' : 'text-[9px]'}`}>
        <span>{project.kind}</span>
        <span>{project.placeholder ? 'Placeholder' : project.year}</span>
      </div>
      <span className={`display ${big ? 'text-[14vw] tab:text-[10rem]' : 'text-3xl'}`}>{project.title}</span>
    </div>
  )
}
