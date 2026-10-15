// Click moves for the hero doodle (docs/ANIMATION_PLAN.md, section 2).
//
// A move is a list of poses on a 0..1 timeline. Each pose sets only the channels it cares about; a
// channel eases (smoothstep) from one key that sets it to the next. Units are the doodle SVG's own
// (about 3 per pixel of the original drawing); angles are degrees, + is clockwise. Arms hang down at 0:
// arm-l + swings the left arm out and up, arm-r - does the same for the right arm.

export type Channel =
  | 'bodyX' | 'bodyY' | 'bodyR' | 'bodySX' | 'bodySY' // whole figure, about the feet
  | 'upperY' | 'upperR' // torso and everything on it, about the hips
  | 'headX' | 'headY' | 'headR'
  | 'pupilsX' | 'pupilsY' | 'pupilsS'
  | 'armL' | 'foreL' | 'armR' | 'foreR'
  | 'shadowS'

export type Pose = Partial<Record<Channel, number>>
export type Move = { name: string; duration: number; line?: string; keys: [number, Pose][] }

const ONES: Channel[] = ['bodySX', 'bodySY', 'pupilsS', 'shadowS']
export const rest = (c: Channel) => (ONES.includes(c) ? 1 : 0)

const smooth = (t: number) => t * t * (3 - 2 * t)

/** Value of every channel at progress p (0..1). Channels a move never touches stay at rest. */
export function sample(move: Move, p: number): Record<Channel, number> {
  const out = {} as Record<Channel, number>
  const channels = new Set<Channel>()
  move.keys.forEach(([, pose]) => Object.keys(pose).forEach(c => channels.add(c as Channel)))
  for (const c of channels) {
    // the channel's own keys, starting and ending at rest
    const keys: [number, number][] = [[0, rest(c)]]
    move.keys.forEach(([t, pose]) => pose[c] !== undefined && keys.push([t, pose[c]!]))
    if (keys[keys.length - 1][0] < 1) keys.push([1, rest(c)])
    let v = keys[keys.length - 1][1]
    for (let i = 0; i < keys.length - 1; i++) {
      const [t0, v0] = keys[i]
      const [t1, v1] = keys[i + 1]
      if (p >= t0 && p <= t1) {
        v = v0 + (v1 - v0) * smooth(t1 > t0 ? (p - t0) / (t1 - t0) : 1)
        break
      }
    }
    out[c] = v
  }
  return out
}

export const MOVES: Record<string, Move> = {
  // Anticipation dip, arm sweeps up in an arc, three waves from the elbow (the hand trailing), settle.
  wave: {
    name: 'wave',
    duration: 1.5,
    line: "Hi! I'm Abhyuday",
    keys: [
      [0.06, { armR: 8, upperR: 0.6 }],
      [0.22, { armR: -150, foreR: -20, headR: 5, upperR: -1, pupilsX: 4 }],
      [0.32, { foreR: -55 }],
      [0.42, { foreR: -15 }],
      [0.52, { foreR: -55 }],
      [0.62, { foreR: -15 }],
      [0.72, { foreR: -50, armR: -148, headR: 5 }],
      [0.9, { armR: 6, foreR: 4, headR: 0, upperR: 0, pupilsX: 0 }],
      [0.96, { armR: -2 }],
    ],
  },
  // Squash, stretch into the air (arms flap up), apex, stretch down, squash on landing, wobble.
  jump: {
    name: 'jump',
    duration: 1.05,
    line: 'Wheee!',
    keys: [
      [0.16, { bodySY: 0.88, bodySX: 1.08, headY: 10, armL: -6, armR: 6, shadowS: 1.05 }],
      [0.3, { bodyY: -230, bodySY: 1.1, bodySX: 0.93, headY: 22, armL: 40, armR: -40, foreL: -30, foreR: 30, shadowS: 0.75 }],
      [0.48, { bodyY: -380, bodySY: 1, bodySX: 1, headY: -8, armL: 55, armR: -55, foreL: -20, foreR: 20, pupilsY: -5, shadowS: 0.6 }],
      [0.68, { bodyY: -60, bodySY: 1.06, bodySX: 0.96, headY: -16, armL: 20, armR: -20, shadowS: 0.9 }],
      [0.76, { bodyY: 0, bodySY: 0.86, bodySX: 1.1, headY: 18, armL: 8, armR: -8, foreL: 0, foreR: 0, pupilsY: 0, shadowS: 1.08 }],
      [0.88, { bodySY: 1.03, bodySX: 0.98, headY: -4 }],
    ],
  },
  // A coin-flip spin: squash, turn through a sliver (the drawing reads the same mirrored), pop back.
  spin: {
    name: 'spin',
    duration: 1.0,
    line: 'Ta-da!',
    keys: [
      [0.12, { bodySY: 0.92, bodySX: 1.05, armL: -4, armR: 4 }],
      [0.3, { bodySX: 0.05, bodySY: 1.06, bodyY: -60, armL: 30, armR: -30 }],
      [0.45, { bodySX: -1, bodySY: 1.04, bodyY: -90 }],
      [0.6, { bodySX: 0.05, bodySY: 1.06, bodyY: -60 }],
      [0.78, { bodySX: 1.08, bodySY: 0.9, bodyY: 0, armL: 0, armR: 0 }],
      [0.9, { bodySX: 0.98, bodySY: 1.02 }],
    ],
  },
  // Shoulders up, forearms open, palms out, head tilts, eyes up; drop with a little bounce.
  shrug: {
    name: 'shrug',
    duration: 1.1,
    line: 'Bugs? What bugs?',
    keys: [
      [0.2, { upperY: -24, armL: 18, foreL: 70, armR: -18, foreR: -70, headR: 7, headY: -4, pupilsY: -7, pupilsX: -4 }],
      [0.62, { upperY: -26, armL: 20, foreL: 74, armR: -20, foreR: -74, headR: 8 }],
      [0.8, { upperY: 4, armL: -3, foreL: -4, armR: 3, foreR: 4, headR: -1, pupilsY: 0, pupilsX: 0 }],
      [0.9, { upperY: -2 }],
    ],
  },
  // Two nods, the head leading and the body following a beat later.
  nod: {
    name: 'nod',
    duration: 0.9,
    line: "Yep, that's me",
    keys: [
      [0.14, { headY: 22, upperY: 2, pupilsY: 4 }],
      [0.3, { headY: -8, upperY: 6 }],
      [0.46, { headY: 20, upperY: -2 }],
      [0.62, { headY: -6, upperY: 4, pupilsY: 0 }],
      [0.8, { headY: 2, upperY: 0 }],
    ],
  },
  // Points down at the work section: turns that way, arm out and down, eyes follow, holds, settles.
  look: {
    name: 'look',
    duration: 1.5,
    line: 'My work is down there',
    keys: [
      [0.08, { armL: -6 }],
      [0.26, { armL: 42, foreL: 8, headR: -6, headX: -10, pupilsX: -8, pupilsY: 10, upperR: -0.8 }],
      [0.72, { armL: 44, foreL: 10, headR: -7, pupilsX: -9, pupilsY: 11 }],
      [0.9, { armL: -4, foreL: -3, headR: 0, headX: 0, pupilsX: 0, pupilsY: 0, upperR: 0 }],
    ],
  },
  // Rare: rapid clicks startle him. Jumps back stretched, arms fling, pupils shrink, recovers.
  startled: {
    name: 'startled',
    duration: 1.1,
    line: 'Whoa! Easy there',
    keys: [
      [0.1, { bodyY: -150, bodyX: 40, bodySY: 1.12, bodySX: 0.92, armL: 62, armR: -62, foreL: 25, foreR: -25, headY: 16, pupilsS: 0.55, shadowS: 0.8 }],
      [0.3, { bodyY: -60, bodyX: 60, bodySY: 1.04, bodySX: 0.98, armL: 50, armR: -50, pupilsS: 0.6 }],
      [0.42, { bodyY: 0, bodyX: 60, bodySY: 0.9, bodySX: 1.08, armL: 20, armR: -20, foreL: 5, foreR: -5, headY: -6, shadowS: 1.05 }],
      [0.7, { bodyX: 20, bodySY: 1.02, bodySX: 0.99, armL: 2, armR: -2, foreL: 0, foreR: 0, pupilsS: 1, headY: 0, shadowS: 1 }],
    ],
  },
}

// Click order: a wave first, then the rest in turn, never the same twice in a row.
export const ROTATION = ['wave', 'jump', 'shrug', 'look', 'spin', 'nod']
