// Everything personal lives here. Replace the placeholders marked TODO.
export const site = {
  alias: 'mrdev4u',
  handle: 'mr.dev4u',
  wordmark: 'mr.developer4u', // the giant footer wordmark
  name: 'Abhyuday Saksena',
  role: 'Creative developer',
  url: 'https://www.mrdev4u.com',
  description:
    'Portfolio of mrdev4u, a creative developer building fast, interactive websites with React, Next.js and WebGL.',
  // TODO: a public contact address (deliberately not your personal email)
  email: 'hello@example.com',
  city: '', // TODO: your city, shown next to your local time
  timeZone: 'UTC', // TODO: your IANA time zone, e.g. 'Europe/Berlin'
  available: true,
  socials: [
    { label: 'GitHub', href: 'https://github.com/abhyudaysaksena06' },
    { label: 'LinkedIn', href: 'https://www.linkedin.com/' }, // TODO
    { label: 'Instagram', href: 'https://www.instagram.com/' }, // TODO
  ],
  nav: [
    { label: 'Work', href: '/work' },
    { label: 'About', href: '/about' },
    { label: 'Contact', href: '/contact' },
  ],
  toolkit: [
    'React',
    'Next.js',
    'TypeScript',
    'Three.js',
    'React Three Fiber',
    'Motion',
    'Tailwind CSS',
    'Node.js',
    'GLSL',
    'Figma',
  ],
} as const

export const services = [
  {
    title: 'Frontend',
    text: 'Fast, accessible interfaces in React and Next.js, typed end to end and built to score 90+ on real phones.',
    items: ['Next.js apps and sites', 'Design systems', 'Performance tuning'],
  },
  {
    title: '3D & motion',
    text: 'Interactive moments people remember: WebGL scenes, scroll choreography and micro-interactions with a reason to exist.',
    items: ['Three.js / R3F scenes', 'Scroll-linked motion', 'Micro-interactions'],
  },
  {
    title: 'Interface design',
    text: 'From rough idea to a clickable prototype, designed in the browser as much as in Figma.',
    items: ['UX flows', 'Visual design', 'Prototyping'],
  },
] as const

export const values = [
  { title: 'Fast.', text: 'Every page is budgeted: it has to feel instant on a mid-range phone.' },
  { title: 'Details.', text: 'Easing curves, spacing and copy get the same care as the code.' },
  { title: 'Accessible.', text: 'Keyboard, screen readers and reduced motion work from day one.' },
  { title: 'Typed.', text: 'TypeScript everywhere, so changes stay safe as the project grows.' },
  { title: 'Clear.', text: 'Plain updates, honest timelines and no surprises.' },
  { title: 'Playful.', text: 'One memorable interaction beats ten forgettable ones.' },
] as const
