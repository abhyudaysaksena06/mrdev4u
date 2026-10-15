import { LineReveal } from './motion'
import { Magnetic, Pill } from './ui'

// The dark "let's talk" card repeated at the end of every page (Grigoletti pattern).
export function CtaCard() {
  return (
    <section className="px-4 pt-24 tab:px-8">
      <div className="flex min-h-[70svh] flex-col items-center justify-center gap-8 rounded-lg bg-ink px-6 py-24 text-center text-paper">
        <p className="font-mono text-xs uppercase text-paper/60">Got an idea?</p>
        <LineReveal lines={["Let's build", 'something good']} className="display text-[15vw] tab:text-[9rem] desk:text-[11rem]" />
        <Magnetic>
          <Pill href="/contact" size="lg" variant="outline" cursor="Say hi">
            Get in touch
          </Pill>
        </Magnetic>
      </div>
    </section>
  )
}
