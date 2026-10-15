'use client'
import { motion, useScroll, useTransform, type MotionValue } from 'motion/react'
import { useRef } from 'react'
import { services } from '@/lib/site'
import { useReduced } from '@/lib/motion-pref'

// Stacking cards: each card pins near the top of the screen and the next one slides over it.
// Cards underneath shrink and dim a little, so the stack reads as a deck rather than overlap,
// and each card's own content is fully visible while it is on top.
export function ServiceStack() {
  const container = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({ target: container, offset: ['start start', 'end end'] })
  const n = services.length
  return (
    <div ref={container} className="relative mt-24">
      {services.map((s, i) => (
        <Card key={s.title} index={i} total={n} progress={scrollYProgress} service={s} />
      ))}
    </div>
  )
}

function Card({
  index,
  total,
  progress,
  service,
}: {
  index: number
  total: number
  progress: MotionValue<number>
  service: (typeof services)[number]
}) {
  const reduce = useReduced()
  const depth = total - 1 - index // how many cards will land on top of this one
  const range = [index / total, 1]
  const scale = useTransform(progress, range, [1, 1 - depth * 0.05])
  const dim = useTransform(progress, range, [0, depth * 0.22])

  return (
    <div className="sticky top-0 flex h-[88svh] items-start pt-[12svh] tab:pt-[14svh]">
      <motion.article
        style={{ scale: reduce ? 1 : scale, top: index * 28 }}
        className="relative w-full origin-top overflow-hidden rounded-xl border border-paper/10 bg-card px-5 shadow-[0_-12px_40px_rgba(0,0,0,0.25)] tab:px-10"
      >
        {/* darkens cards as they sink into the stack */}
        <motion.div
          aria-hidden
          style={{ opacity: reduce ? 0 : dim }}
          className="pointer-events-none absolute inset-0 z-10 bg-black"
        />
        <header className="grid grid-cols-12 items-baseline border-b border-paper/15 py-6 tab:py-8">
          <span className="display col-span-3 text-4xl tab:text-6xl">0{index + 1}.</span>
          <h3 className="display col-span-8 text-4xl tab:text-6xl">{service.title}</h3>
          <span aria-hidden className="col-span-1 justify-self-end font-mono text-xs text-paper/60">
            0{index + 1}/0{total}
          </span>
        </header>
        <div className="grid grid-cols-12 gap-y-8 py-8 tab:py-12">
          <p className="col-span-12 max-w-md text-lg text-paper/70 tab:col-span-5 tab:col-start-4">{service.text}</p>
          <ul className="col-span-12 tab:col-span-4 tab:col-start-9">
            {service.items.map((it, j) => (
              <li key={it} className="flex items-baseline gap-4 border-b border-paper/15 py-2.5 last:border-b-0">
                <span className="font-mono text-xs text-paper/60">0{j + 1}</span>
                <span className="display text-xl tab:text-2xl">{it}</span>
              </li>
            ))}
          </ul>
        </div>
      </motion.article>
    </div>
  )
}
