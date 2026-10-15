'use client'
import { Canvas, useFrame } from '@react-three/fiber'
import { useRef } from 'react'
import * as THREE from 'three'
import { LogoMeshes, Lights } from './LogoMeshes'

type Props = {
  compact?: boolean // scattered pieces need more room
  assembled: React.RefObject<number> // 0 scattered, 1 assembled
  spinKick: React.RefObject<number> // extra angular velocity added by clicks
}

// Drag horizontally to spin; momentum decays; idles with a slow turn.
function Toy({ assembled, spinKick, drag, scale }: Props & { drag: React.RefObject<{ v: number; active: boolean }>; scale: number }) {
  const group = useRef<THREE.Group>(null!)
  const vel = useRef(0.4)
  useFrame((state, dt) => {
    const d = drag.current
    if (spinKick.current) {
      vel.current += spinKick.current
      spinKick.current = 0
    }
    if (d.active) vel.current = d.v
    else vel.current = THREE.MathUtils.damp(vel.current, 0.4, 1.2, dt)
    group.current.rotation.y += vel.current * dt
    group.current.rotation.x = THREE.MathUtils.damp(group.current.rotation.x, -state.pointer.y * 0.25, 4, dt)
  })
  return (
    <group ref={group} scale={scale}>
      <LogoMeshes assembled={assembled} />
    </group>
  )
}

export default function LogoToy3D({ assembled, spinKick, compact }: Props) {
  const drag = useRef({ v: 0, active: false, x: 0, t: 0 })
  return (
    <Canvas
      flat // no filmic tone mapping: keeps the brand orange true
      dpr={[1, 1.5]}
      camera={{ position: [0, 0, 6], fov: 30 }}
      gl={{ antialias: true, alpha: true }}
      className="!touch-pan-y"
      onPointerDown={e => {
        drag.current = { v: 0, active: true, x: e.clientX, t: performance.now() }
        ;(e.target as Element).setPointerCapture?.(e.pointerId)
      }}
      onPointerMove={e => {
        const d = drag.current
        if (!d.active) return
        const now = performance.now()
        const dt = Math.max(now - d.t, 1) / 1000
        d.v = THREE.MathUtils.clamp(((e.clientX - d.x) / dt) * 0.01, -25, 25)
        d.x = e.clientX
        d.t = now
      }}
      onPointerUp={() => (drag.current.active = false)}
      onPointerCancel={() => (drag.current.active = false)}
      aria-hidden
    >
      <Lights />
      <Toy assembled={assembled} spinKick={spinKick} drag={drag} scale={compact ? 0.72 : 1.25} />
    </Canvas>
  )
}
