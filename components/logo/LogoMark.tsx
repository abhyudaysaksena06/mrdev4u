import { LOGO_W, PIECES, piecePath } from './geometry'

// Flat SVG version of the "M/" monogram: nav, favicon-sized uses, fallback for the 3D logo.
export function LogoMark({ className, title = 'mrdev4u' }: { className?: string; title?: string }) {
  return (
    <svg viewBox={`-0.02 -0.02 ${LOGO_W + 0.04} 1.04`} className={className} role="img" aria-label={title}>
      {PIECES.map(p => (
        <path
          key={p.id}
          d={piecePath(p)}
          fill={p.accent ? 'var(--accent)' : 'currentColor'}
          stroke={p.accent ? 'var(--accent)' : 'currentColor'}
          strokeWidth={0.006} // hides hairline seams between pieces
          strokeLinejoin="round"
        />
      ))}
    </svg>
  )
}
