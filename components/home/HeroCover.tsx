'use client'
import { motion, useScroll, useTransform } from 'motion/react'
import { useReduced } from '@/lib/motion-pref'
import { useRef } from 'react'

// Pins the hero; as the next (dark) panel slides over it, the hero fades and shrinks a little.
export function HeroCover({ children }: { children: React.ReactNode }) {
  const ref = useRef<HTMLElement>(null)
  const reduce = useReduced()
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start start', 'end start'] })
  const opacity = useTransform(scrollYProgress, [0, 0.9], [1, 0])
  const scale = useTransform(scrollYProgress, [0, 1], [1, 0.92])
  const y = useTransform(scrollYProgress, [0, 1], ['0%', '12%'])
  return (
    <section ref={ref} className="sticky top-0 min-h-svh">
      <motion.div style={reduce ? undefined : { opacity, scale, y }} className="min-h-svh origin-top">
        {children}
      </motion.div>
    </section>
  )
}
