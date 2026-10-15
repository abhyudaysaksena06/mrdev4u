'use client'
import { useSyncExternalStore } from 'react'

// Tiny global store shared by the preloader, hero, nav and 3D logo.
type State = {
  introDone: boolean // preloader finished (or skipped)
}

let state: State = { introDone: false }
const listeners = new Set<() => void>()

export function setStore(patch: Partial<State>) {
  const next = { ...state, ...patch }
  if (Object.keys(patch).every(k => next[k as keyof State] === state[k as keyof State])) return
  state = next
  listeners.forEach(l => l())
}

export function getStore() {
  return state
}

const subscribe = (l: () => void) => {
  listeners.add(l)
  return () => listeners.delete(l)
}

const serverState: State = { introDone: false }

export function useStore<T>(select: (s: State) => T): T {
  return useSyncExternalStore(
    subscribe,
    () => select(state),
    () => select(serverState),
  )
}
