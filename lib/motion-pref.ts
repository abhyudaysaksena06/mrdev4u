'use client'
import { useSyncExternalStore } from 'react'

// Motion preference lives on <html data-motion="full|reduce">. The head script sets it from
// the visitor's saved choice, else from the OS setting (data-motion-source="system").
// The nav toggle lets people who have animations off at OS level opt back in.

export type Motion = 'full' | 'reduce'

export const isReduced = () =>
  typeof document !== 'undefined' && document.documentElement.dataset.motion === 'reduce'

export function setMotion(m: Motion) {
  const root = document.documentElement
  root.dataset.motion = m
  root.dataset.motionSource = 'user'
  try {
    localStorage.setItem('motion', m)
  } catch {}
  window.dispatchEvent(new Event('motionchange'))
}

const subscribe = (cb: () => void) => {
  window.addEventListener('motionchange', cb)
  return () => window.removeEventListener('motionchange', cb)
}

// True when motion should be reduced. Server render assumes full motion.
export function useReduced() {
  return useSyncExternalStore(subscribe, isReduced, () => false)
}
