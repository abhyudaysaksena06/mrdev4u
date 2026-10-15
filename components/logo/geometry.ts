// The "m/" monogram, defined once and drawn both as SVG and as extruded 3D.
// Units: the mark is LOGO_W wide and 1 tall, origin bottom-left, y up.

export type Piece =
  | { id: string; kind: 'rect'; x: number; y: number; w: number; h: number; r?: [number, number, number, number]; accent?: boolean }
  | { id: string; kind: 'poly'; points: [number, number][]; accent?: boolean }

export const LOGO_W = 1.98

export const PIECES: Piece[] = [
  // corner radii order: top-left, top-right, bottom-right, bottom-left
  { id: 'top', kind: 'rect', x: 0, y: 0.72, w: 1.24, h: 0.28, r: [0.28, 0.28, 0, 0] },
  { id: 'stem-l', kind: 'rect', x: 0, y: 0, w: 0.26, h: 0.74 },
  { id: 'stem-m', kind: 'rect', x: 0.49, y: 0, w: 0.26, h: 0.74 },
  { id: 'stem-r', kind: 'rect', x: 0.98, y: 0, w: 0.26, h: 0.74 },
  { id: 'slash', kind: 'poly', points: [[1.38, 0], [1.62, 0], [1.98, 1], [1.74, 1]], accent: true },
]

// Where each piece starts before it assembles (preloader) or where it lies (404).
// dx, dy in logo units, rot in degrees.
export const SCATTER: Record<string, { dx: number; dy: number; rot: number }> = {
  top: { dx: -0.9, dy: 1.1, rot: -38 },
  'stem-l': { dx: -1.5, dy: -0.8, rot: 24 },
  'stem-m': { dx: 0.2, dy: -1.3, rot: -62 },
  'stem-r': { dx: 1.2, dy: 1.3, rot: 48 },
  slash: { dx: 1.6, dy: -0.6, rot: -30 },
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
