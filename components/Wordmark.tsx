'use client'
import { motion } from 'motion/react'
import { useEffect, useRef, useState } from 'react'
import { useReduced } from '@/lib/motion-pref'
import { EASE } from './motion'

/**
 * Edge-to-edge wordmark (Superfluid-style footer). The font size is fitted to the
 * container width; letters rise in on scroll and each one jumps and turns orange on hover.
 */
export function Wordmark({ text }: { text: string }) {
  const box = useRef<HTMLDivElement>(null)
  const measure = useRef<HTMLSpanElement>(null)
  const [size, setSize] = useState<number | null>(null)
  const reduce = useReduced()

  useEffect(() => {
    const fit = () => {
      if (!box.current || !measure.current) return
      const natural = measure.current.getBoundingClientRect().width // width at 100px
      const cs = getComputedStyle(box.current)
      const inner = box.current.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight)
      if (natural) setSize((inner / natural) * 100)
    }
    document.fonts.ready.then(fit)
    const ro = new ResizeObserver(fit)
    if (box.current) ro.observe(box.current)
    return () => ro.disconnect()
  }, [])

  const letters = [...text.toUpperCase()]
  return (
    <div ref={box} className="relative px-4 tab:px-6" aria-label={text} role="img">
      {/* hidden copy at 100px used to fit the real one to the width */}
      <span ref={measure} aria-hidden className="display pointer-events-none invisible absolute left-0 top-0 whitespace-nowrap text-[100px]">
        {text.toUpperCase()}
      </span>
      <motion.p
        aria-hidden
        className="display flex justify-between overflow-hidden whitespace-nowrap leading-[0.8]"
        style={{ fontSize: size ? `${size * 0.99}px` : '23vw' }}
        initial="hidden"
        whileInView="shown"
        viewport={{ once: true, amount: 0.4 }}
      >
        {letters.map((ch, i) => (
          <motion.span
            key={i}
            className={`inline-block cursor-default pt-[0.04em] transition-[color,translate] duration-300 ease-soft hover:-translate-y-[6%] hover:text-accent ${ch === '.' ? 'text-accent' : ''}`}
            variants={{
              hidden: { y: reduce ? 0 : '100%', opacity: reduce ? 0 : 1 },
              shown: { y: 0, opacity: 1, transition: { duration: reduce ? 0.2 : 0.8, ease: EASE, delay: reduce ? 0 : i * 0.05 } },
            }}
          >
            {ch}
          </motion.span>
        ))}
      </motion.p>
    </div>
  )
}
