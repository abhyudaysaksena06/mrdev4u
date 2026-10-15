export type Project = {
  slug: string
  title: string
  year: number
  kind: string
  role: string
  stack: string[]
  color: string // background of the generated cover
  ink: string // text colour on the cover
  summary: string
  problem: string
  decisions: { title: string; text: string }[]
  result: string
  link?: string
  placeholder?: boolean
}

// TODO: replace the placeholder projects with your own work.
export const projects: Project[] = [
  {
    slug: 'mrdev4u',
    title: 'mrdev4u',
    year: 2026,
    kind: 'Portfolio',
    role: 'Design and development',
    stack: ['Next.js', 'React Three Fiber', 'Motion', 'Tailwind'],
    color: '#ff4c24',
    ink: '#111111',
    summary: 'This site: an editorial portfolio with a 3D logo that travels from the preloader into the nav.',
    problem:
      'Most motion-heavy portfolios look great and load slowly. The goal was award-level motion with a 90+ mobile performance score.',
    decisions: [
      {
        title: 'One easing curve',
        text: 'Every reveal and hover uses cubic-bezier(0.12, 0.23, 0.5, 1), so the whole site moves with one voice.',
      },
      {
        title: 'Procedural 3D logo',
        text: 'The monogram is extruded from five 2D shapes at runtime, so there is no model file to download.',
      },
      {
        title: '3D after first paint',
        text: 'Three.js loads only after the page is usable; an SVG version of the logo stands in until then and for reduced motion.',
      },
    ],
    result: 'A static site with view transitions, a cursor-reactive 3D hero and a full reduced-motion mode.',
    link: 'https://github.com/abhyudaysaksena06/mrdev4u',
  },
  {
    slug: 'project-two',
    title: 'Project two',
    year: 2026,
    kind: 'Web app',
    role: 'Your role',
    stack: ['Your', 'Stack'],
    color: '#2a2a2a',
    ink: '#ebe9e4',
    summary: 'Placeholder. Replace with a one-line description of a real project in lib/projects.ts.',
    problem: 'Placeholder. What was the problem, and for whom?',
    decisions: [
      { title: 'Decision one', text: 'Placeholder. A key decision and why you made it.' },
      { title: 'Decision two', text: 'Placeholder. Another decision, ideally with a visual.' },
    ],
    result: 'Placeholder. The outcome, with a number if you have one.',
    placeholder: true,
  },
  {
    slug: 'project-three',
    title: 'Project three',
    year: 2025,
    kind: 'Website',
    role: 'Your role',
    stack: ['Your', 'Stack'],
    color: '#d9d6cf',
    ink: '#111111',
    summary: 'Placeholder. Replace with a one-line description of a real project in lib/projects.ts.',
    problem: 'Placeholder. What was the problem, and for whom?',
    decisions: [
      { title: 'Decision one', text: 'Placeholder. A key decision and why you made it.' },
      { title: 'Decision two', text: 'Placeholder. Another decision, ideally with a visual.' },
    ],
    result: 'Placeholder. The outcome, with a number if you have one.',
    placeholder: true,
  },
]

export const getProject = (slug: string) => projects.find(p => p.slug === slug)
