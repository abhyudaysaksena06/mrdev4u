'use client'
import dynamic from 'next/dynamic'
import { useEffect, useRef, useState } from 'react'
import { LOGO_W, PIECES, SCATTER, piecePath } from './geometry'
import { canUse3D } from './LogoMeshes'

const LogoToy3D = dynamic(() => import('./LogoToy3D'), { ssr: false })

/**
 * A logo you can play with. `mode="footer"`: assembled, drag to spin, five clicks for a surprise.
 * `mode="broken"` (404): starts in pieces; the button puts it back together.
 * Loads 3D only when near the viewport; falls back to an SVG with the same behaviour.
 */
export function LogoToy({ mode = 'footer', className = '' }: { mode?: 'footer' | 'broken'; className?: string }) {
  const box = useRef<HTMLDivElement>(null)
  const [use3d, setUse3d] = useState(false)
  const [whole, setWhole] = useState(mode === 'footer')
  const [msg, setMsg] = useState<string | null>(null)
  const assembled = useRef(mode === 'footer' ? 1 : 0)
  const spinKick = useRef(0)
  const clicks = useRef<number[]>([])

  useEffect(() => {
    if (!canUse3D() || !box.current) return
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          setUse3d(true)
          io.disconnect()
        }
      },
      { rootMargin: '300px' },
    )
    io.observe(box.current)
    return () => io.disconnect()
  }, [])

  useEffect(() => {
    assembled.current = whole ? 1 : 0
  }, [whole])

  // Five quick clicks: the logo bursts apart and snaps back.
  const onClick = () => {
    if (mode !== 'footer') return
    const now = performance.now()
    clicks.current = [...clicks.current.filter(t => now - t < 1600), now]
    spinKick.current += 2.5
    if (clicks.current.length >= 5) {
      clicks.current = []
      setWhole(false)
      setMsg('You found it. Thanks for playing.')
      setTimeout(() => setWhole(true), 900)
      setTimeout(() => setMsg(null), 3200)
    }
  }

  return (
    <div className={className}>
      <div
        ref={box}
        className="relative aspect-[1.6/1] w-full cursor-grab select-none active:cursor-grabbing"
        data-cursor={mode === 'footer' ? 'Drag me' : undefined}
        onClick={onClick}
      >
        {use3d ? (
          <LogoToy3D assembled={assembled} spinKick={spinKick} compact={mode === 'broken'} />
        ) : (
          <svg viewBox={`-0.4 -0.3 ${LOGO_W + 0.8} 1.6`} className="size-full overflow-visible text-ink" aria-hidden>
            {PIECES.map(p => {
              const s = SCATTER[p.id]
              return (
                <path
                  key={p.id}
                  d={piecePath(p)}
                  fill={p.accent ? 'var(--accent)' : 'currentColor'}
                  stroke={p.accent ? 'var(--accent)' : 'currentColor'}
                  strokeWidth={0.006}
                  style={{
                    transformBox: 'fill-box',
                    transformOrigin: 'center',
                    transition: 'transform .7s var(--ease-out)',
                    transform: whole ? 'none' : `translate(${s.dx * 0.5}px, ${-s.dy * 0.4}px) rotate(${s.rot}deg)`,
                  }}
                />
              )
            })}
          </svg>
        )}
      </div>
      {mode === 'broken' && (
        <button
          type="button"
          onClick={() => setWhole(w => !w)}
          className="mt-6 rounded-[4px] border border-ink px-4 py-3 font-display text-lg uppercase hover:bg-ink hover:text-paper"
        >
          {whole ? 'Break it again' : 'Put it back together'}
        </button>
      )}
      <p aria-live="polite" className="mt-2 h-5 font-mono text-xs uppercase text-body">
        {msg}
      </p>
    </div>
  )
}
