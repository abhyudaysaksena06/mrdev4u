'use client'
import { useFrame, useThree } from '@react-three/fiber'
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js'
import { useEffect, useMemo, useRef } from 'react'
import * as THREE from 'three'
import { LOGO_W, PIECES, SCATTER, type Piece } from './geometry'

const DEPTH = 0.3

function shapeOf(p: Piece): THREE.Shape {
  const s = new THREE.Shape()
  if (p.kind === 'poly') {
    p.points.forEach(([x, y], i) => (i ? s.lineTo(x, y) : s.moveTo(x, y)))
    s.closePath()
    return s
  }
  const [tl, tr, br, bl] = p.r ?? [0, 0, 0, 0]
  const x0 = p.x, x1 = p.x + p.w, y0 = p.y, y1 = p.y + p.h
  s.moveTo(x0 + bl, y0)
  s.lineTo(x1 - br, y0)
  if (br) s.absarc(x1 - br, y0 + br, br, -Math.PI / 2, 0, false)
  s.lineTo(x1, y1 - tr)
  if (tr) s.absarc(x1 - tr, y1 - tr, tr, 0, Math.PI / 2, false)
  s.lineTo(x0 + tl, y1)
  if (tl) s.absarc(x0 + tl, y1 - tl, tl, Math.PI / 2, Math.PI, false)
  s.lineTo(x0, y0 + bl)
  if (bl) s.absarc(x0 + bl, y0 + bl, bl, Math.PI, Math.PI * 1.5, false)
  return s
}

// Read the theme's ink colour from CSS so the logo follows light/dark mode.
export function useInkColor(material: THREE.MeshStandardMaterial) {
  useEffect(() => {
    const apply = () => {
      const ink = getComputedStyle(document.documentElement).getPropertyValue('--ink').trim() || '#111111'
      material.color.set(ink)
      // A light logo (dark theme) blows out under the same reflections, so dim them.
      material.envMapIntensity = document.documentElement.dataset.theme === 'dark' ? 0.35 : 1.1
    }
    apply()
    window.addEventListener('themechange', apply)
    return () => window.removeEventListener('themechange', apply)
  }, [material])
}

const easeOut = (t: number) => 1 - Math.pow(1 - t, 3)

/**
 * The five extruded pieces of the monogram, centred on the origin, 1 unit tall.
 * `assembled` is a target from 0 (scattered) to 1 (assembled); pieces follow it with a stagger.
 */
export function LogoMeshes({ assembled }: { assembled?: React.RefObject<number> }) {
  const parts = useMemo(
    () =>
      PIECES.map(p => {
        const geo = new THREE.ExtrudeGeometry(shapeOf(p), {
          depth: DEPTH,
          bevelEnabled: true,
          bevelThickness: 0.03,
          bevelSize: 0.018,
          bevelSegments: 3,
          curveSegments: 18,
        })
        geo.computeBoundingBox()
        const c = new THREE.Vector3()
        geo.boundingBox!.getCenter(c)
        geo.translate(-c.x, -c.y, -c.z) // rotate each piece around its own centre
        const home = new THREE.Vector3(c.x - LOGO_W / 2, c.y - 0.5, 0)
        const s = SCATTER[p.id]
        const away = new THREE.Vector3(home.x + s.dx, home.y + s.dy, -0.4 + Math.sin(s.rot) * 0.6)
        return { id: p.id, accent: !!p.accent, geo, home, away, rot: THREE.MathUtils.degToRad(s.rot) }
      }),
    [],
  )
  const ink = useMemo(() => new THREE.MeshStandardMaterial({ color: '#111111', roughness: 0.32, metalness: 0.15, envMapIntensity: 1.1 }), [])
  const accent = useMemo(() => new THREE.MeshStandardMaterial({ color: '#ff4c24', roughness: 0.55, metalness: 0, envMapIntensity: 0.2 }), [])
  useInkColor(ink)

  useEffect(
    () => () => {
      parts.forEach(p => p.geo.dispose())
      ink.dispose()
      accent.dispose()
    },
    [parts, ink, accent],
  )

  const meshes = useRef<(THREE.Mesh | null)[]>([])
  const current = useRef(assembled?.current ?? 1)

  useFrame((_, dt) => {
    const target = assembled?.current ?? 1
    current.current = THREE.MathUtils.damp(current.current, target, 3.2, dt)
    const k = current.current
    parts.forEach((p, i) => {
      const m = meshes.current[i]
      if (!m) return
      const t = easeOut(THREE.MathUtils.clamp(k * 1.35 - i * 0.07, 0, 1))
      m.position.lerpVectors(p.away, p.home, t)
      m.rotation.set((1 - t) * p.rot * 0.8, (1 - t) * -p.rot * 0.6, (1 - t) * p.rot)
    })
  })

  return (
    <group>
      {parts.map((p, i) => (
        <mesh
          key={p.id}
          ref={el => {
            meshes.current[i] = el
          }}
          geometry={p.geo}
          material={p.accent ? accent : ink}
          position={p.home}
        />
      ))}
    </group>
  )
}

// Soft studio lighting: a procedural room environment (no HDR download) plus a key light,
// so the near-black logo still shows its bevels and depth.
export function Lights() {
  const gl = useThree(s => s.gl)
  const scene = useThree(s => s.scene)
  useEffect(() => {
    const pmrem = new THREE.PMREMGenerator(gl)
    const env = pmrem.fromScene(new RoomEnvironment(), 0, 0.1, 100, { size: 64 }).texture // small = cheap to build
    scene.environment = env
    return () => {
      scene.environment = null
      env.dispose()
      pmrem.dispose()
    }
  }, [gl, scene])
  return (
    <>
      <ambientLight intensity={0.15} />
      <directionalLight position={[3, 4, 6]} intensity={0.9} />
      <directionalLight position={[-5, 2, -3]} intensity={0.6} />
    </>
  )
}

export function canUse3D() {
  if (typeof window === 'undefined') return false
  const nav = navigator as Navigator & { connection?: { saveData?: boolean }; deviceMemory?: number }
  if (nav.connection?.saveData) return false
  if ((nav.hardwareConcurrency ?? 8) < 4 || (nav.deviceMemory ?? 8) < 2) return false
  try {
    return !!document.createElement('canvas').getContext('webgl2')
  } catch {
    return false
  }
}
