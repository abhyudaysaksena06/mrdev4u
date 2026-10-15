'use client'
import { motion, useInView, useScroll, useTransform } from 'motion/react'
import { useReduced } from '@/lib/motion-pref'
import { useRef } from 'react'
import { site, values } from '@/lib/site'
import { Magnetic, Pill } from '../ui'

// A small dark box that grows to full width as it scrolls in, then becomes the About section.
export function AboutGrow() {
  const ref = useRef<HTMLDivElement>(null)
  const reduce = useReduced()
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start end', 'start 0.15'] })
  const scale = useTransform(scrollYProgress, [0, 1], [0.55, 1])
  const radius = useTransform(scrollYProgress, [0, 1], [28, 8])
  return (
    <section className="px-4 py-24 tab:px-8" aria-labelledby="about-title">
      <motion.div
        ref={ref}
        style={reduce ? undefined : { scale, borderRadius: radius }}
        className="origin-top overflow-hidden rounded-lg bg-ink text-paper"
      >
        <div className="grid gap-10 px-6 py-24 tab:grid-cols-12 tab:px-10 tab:py-32">
          <div className="tab:col-span-6 tab:col-start-2">
            <div className="flex items-center gap-5">
              <div aria-hidden className="display grid size-20 shrink-0 place-items-center rounded-md bg-accent text-4xl text-[#111]">
                {site.name.charAt(0)}
              </div>
              <h2 id="about-title" className="display text-6xl tab:text-8xl">
                Hey, I&apos;m {site.alias}
              </h2>
            </div>
            <p className="mt-8 max-w-lg text-lg text-paper/70">
              {site.name}, a developer who designs. I care about the parts most people skip: how a page loads, how a button
              answers a click, and how it feels on a cheap phone.
            </p>
            <div className="mt-8">
              <Magnetic>
                <Pill href="/about" variant="outline">
                  More about me
                </Pill>
              </Magnetic>
            </div>
          </div>
        </div>
        <ul className="border-t border-paper/15 px-6 pb-16 tab:px-10">
          {values.map(v => (
            <Value key={v.title} title={v.title} text={v.text} />
          ))}
        </ul>
      </motion.div>
    </section>
  )
}

// The row nearest the middle of the screen lights up.
function Value({ title, text }: { title: string; text: string }) {
  const ref = useRef<HTMLLIElement>(null)
  const on = useInView(ref, { margin: '-45% 0px -45% 0px' })
  return (
    <li
      ref={ref}
      className={`grid grid-cols-12 gap-4 border-b border-paper/15 py-6 transition-colors duration-500 ${on ? 'text-paper' : 'text-paper/55'}`}
    >
      <span className="col-span-12 text-2xl tab:col-span-4 tab:text-right tab:text-3xl">{title}</span>
      <span className="col-span-12 text-lg tab:col-span-6 tab:col-start-6 tab:text-2xl">{text}</span>
    </li>
  )
}
