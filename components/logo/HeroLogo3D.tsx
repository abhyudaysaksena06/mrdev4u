'use client'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { setStore } from '@/lib/store'
import { LOGO_W } from './geometry'
import { LogoMeshes, Lights } from './LogoMeshes'

const { damp, lerp, clamp } = THREE.MathUtils

// Dock progress: 0 in the hero, 1 once the logo sits in the nav slot.
const dockProgress = () => clamp(window.scrollY / (window.innerHeight * 0.65), 0, 1)

function Logo({ anchorId, slotId }: { anchorId: string; slotId: string }) {
  const outer = useRef<THREE.Group>(null!)
  const inner = useRef<THREE.Group>(null!)
  const spin = useRef(-Math.PI * 1.25) // enters with a turn from flat to 3D
  const tilt = useRef(new THREE.Vector2())
  const first = useRef(true)
  const setFrameloop = useThree(s => s.setFrameloop)

  // Stop rendering once docked; resume when scrolling back up.
  useEffect(() => {
    let docked = false
    const onScroll = () => {
      const now = dockProgress() >= 0.999
      if (now === docked) return
      docked = now
      setStore({ docked: now })
      setFrameloop(now ? 'never' : 'always')
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    onScroll()
    return () => window.removeEventListener('scroll', onScroll)
  }, [setFrameloop])

  useFrame((state, dt) => {
    const anchor = document.getElementById(anchorId)?.getBoundingClientRect()
    const slot = document.getElementById(slotId)?.getBoundingClientRect()
    if (!anchor || !slot) return
    const p = dockProgress()
    const e = p * p * (3 - 2 * p) // smoothstep

    // Screen px -> world units on the z = 0 plane.
    const { width: vw, height: vh } = state.viewport
    const { width: sw, height: sh } = state.size
    const u = vh / sh
    const toWorld = (x: number, y: number) => [(x / sw - 0.5) * vw, -(y / sh - 0.5) * vh] as const

    const [ax, ay] = toWorld(anchor.left + anchor.width / 2, anchor.top + anchor.height / 2)
    const [sx, sy] = toWorld(slot.left + slot.width / 2, slot.top + slot.height / 2)
    const heroScale = Math.min(anchor.height * u * 0.82, (anchor.width * u * 0.82) / LOGO_W)
    const slotScale = Math.min(slot.height * u, (slot.width * u) / LOGO_W) * 0.94

    outer.current.position.set(lerp(ax, sx, e), lerp(ay, sy, e), 0)
    outer.current.scale.setScalar(lerp(heroScale, slotScale, e))

    // Cursor tilt and idle spin fade out while docking, ending face-on like the flat mark.
    tilt.current.x = damp(tilt.current.x, -state.pointer.y * 0.35, 5, dt)
    tilt.current.y = damp(tilt.current.y, state.pointer.x * 0.55, 5, dt)
    spin.current = damp(spin.current, 0, 1.8, dt) // entrance turn settles
    const sway = Math.sin(state.clock.elapsedTime * 0.6) * 0.3
    inner.current.rotation.x = tilt.current.x * (1 - e)
    inner.current.rotation.y = (tilt.current.y + spin.current + sway) * (1 - e)

    if (first.current) {
      first.current = false
      setStore({ logo3d: true })
    }
  })

  return (
    <group ref={outer}>
      <group ref={inner}>
        <LogoMeshes />
      </group>
    </group>
  )
}

export default function HeroLogo3D({ anchorId, slotId }: { anchorId: string; slotId: string }) {
  useEffect(() => () => setStore({ logo3d: false, docked: false }), [])
  return (
    <Canvas
      flat // no filmic tone mapping: keeps the brand orange true
      className="!pointer-events-none !fixed !inset-0 z-[55]"
      dpr={[1, 1.5]}
      camera={{ position: [0, 0, 8], fov: 30 }}
      gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
      eventSource={typeof document !== 'undefined' ? document.body : undefined}
      eventPrefix="client"
      aria-hidden
    >
      <Lights />
      <Logo anchorId={anchorId} slotId={slotId} />
    </Canvas>
  )
}
