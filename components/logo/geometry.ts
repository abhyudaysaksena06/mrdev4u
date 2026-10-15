// The "M/" monogram, defined once and drawn both as SVG and as extruded 3D.
// The orange piece is both the M's right leg and a developer's slash ("</>").
// Pieces tile edge to edge without overlapping, so the 3D extrusion renders cleanly.
// Units: the mark is LOGO_W wide and 1 tall, origin bottom-left, y up.

export type Piece =
  | { id: string; kind: 'rect'; x: number; y: number; w: number; h: number; r?: [number, number, number, number]; accent?: boolean }
  | { id: string; kind: 'poly'; points: [number, number][]; accent?: boolean }

export const LOGO_W = 1.4

export const PIECES: Piece[] = [
  { id: 'stem-l', kind: 'poly', points: [[0, 0], [0.26, 0], [0.26, 0.653], [0, 1]] },
  { id: 'diag', kind: 'poly', points: [[0, 1], [0.32, 1], [0.86, 0.28], [0.54, 0.28]] },
  { id: 'slash', kind: 'poly', points: [[1.08, 1], [1.4, 1], [0.86, 0.28], [0.7, 0.4933]], accent: true },
  { id: 'stem-r', kind: 'poly', points: [[1.14, 0], [1.4, 0], [1.4, 1], [1.14, 0.653]] },
]

// Where each piece starts before it assembles (preloader) or where it lies (404).
// dx, dy in logo units, rot in degrees.
export const SCATTER: Record<string, { dx: number; dy: number; rot: number }> = {
  'stem-l': { dx: -1.3, dy: -0.7, rot: 28 },
  diag: { dx: -0.6, dy: 1.15, rot: -42 },
  slash: { dx: 1.3, dy: 0.9, rot: 36 },
  'stem-r': { dx: 1.1, dy: -1.1, rot: -58 },
}

// SVG path for a piece, in a viewBox of `0 0 LOGO_W 1` with y flipped.
export function piecePath(p: Piece): string {
  const fy = (y: number) => +(1 - y).toFixed(4)
  if (p.kind === 'poly') {
    return 'M' + p.points.map(([x, y]) => `${x} ${fy(y)}`).join('L') + 'Z'
  }
  const [tl, tr, br, bl] = p.r ?? [0, 0, 0, 0]
  const x0 = p.x, x1 = p.x + p.w, y0 = fy(p.y + p.h), y1 = fy(p.y) // y0 = top edge in SVG space
  return [
    `M${x0 + tl} ${y0}`,
    `H${x1 - tr}`,
    tr ? `A${tr} ${tr} 0 0 1 ${x1} ${y0 + tr}` : '',
    `V${y1 - br}`,
    br ? `A${br} ${br} 0 0 1 ${x1 - br} ${y1}` : '',
    `H${x0 + bl}`,
    bl ? `A${bl} ${bl} 0 0 1 ${x0} ${y1 - bl}` : '',
    `V${y0 + tl}`,
    tl ? `A${tl} ${tl} 0 0 1 ${x0 + tl} ${y0}` : '',
    'Z',
  ].join('')
}
