import type { Metadata } from 'next'
import { site } from '@/lib/site'
import { IntroFade, IntroLines } from '@/components/intro'
import { ContactForm } from '@/components/ContactForm'
import { LocalTime } from '@/components/ui'

export const metadata: Metadata = {
  title: 'Contact',
  description: `Get in touch with ${site.alias}.`,
}

export default function ContactPage() {
  return (
    <section className="px-4 pt-36 pb-12 tab:px-8 tab:pt-44" style={{ ['--intro-base' as string]: '0.05s' }}>
      <div className="grid gap-8 tab:grid-cols-12">
        <div className="tab:col-span-7">
          <IntroLines lines={['Say hello']} className="display text-[24vw] tab:text-[13rem]" />
        </div>
        <IntroFade delay={200} className="max-w-sm self-end text-lg text-body tab:col-span-5">
          <p>Have a project, a role or just a question? Write to me; I usually answer within two days.</p>
        </IntroFade>
      </div>

      <div className="mt-24 grid gap-16 tab:grid-cols-12">
        <div className="space-y-10 tab:col-span-4">
          <div>
            <p className="mb-2 font-mono text-xs uppercase text-muted">Email</p>
            <a href={`mailto:${site.email}`} className="text-2xl font-medium underline-offset-4 hover:text-accent hover:underline">
              {site.email}
            </a>
          </div>
          <div>
            <p className="mb-2 font-mono text-xs uppercase text-muted">Elsewhere</p>
            <ul className="space-y-1">
              {site.socials.map(s => (
                <li key={s.label}>
                  <a href={s.href} target="_blank" rel="noreferrer" className="text-lg text-body hover:text-ink">
                    {s.label} ↗
                  </a>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="mb-2 font-mono text-xs uppercase text-muted">My time</p>
            <LocalTime />
          </div>
        </div>
        <div className="tab:col-span-7 tab:col-start-6">
          <ContactForm />
        </div>
      </div>
    </section>
  )
}
