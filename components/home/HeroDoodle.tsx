'use client'
import { useEffect, useRef } from 'react'
import { setStore } from '@/lib/store'
import { isReduced } from '@/lib/motion-pref'

// Marks the intro as finished once the CSS preloader timeline has played.
function useIntroClock() {
  useEffect(() => {
    const root = document.documentElement
    // Matches the CSS timeline: full intro ~1.9 s, reduced ~0.8 s, skipped on client-side returns.
    const wait = root.classList.contains('no-intro') ? 0 : isReduced() ? 800 : 1900
    const id = setTimeout(() => {
      root.classList.add('no-intro') // navigating back to home inside the site skips the preloader
      setStore({ introDone: true })
    }, wait)
    return () => clearTimeout(id)
  }, [])
}

const INTRO_MS = 1900

// The wave is a plain H.264 video with the colour in the top half and the alpha matte in the bottom
// half (so it is small and plays everywhere); this shader puts the two back together on a canvas.
const VERT = `attribute vec2 p; varying vec2 uv;
void main() { uv = vec2(p.x * .5 + .5, .5 - p.y * .5); gl_Position = vec4(p, 0., 1.); }`
const FRAG = `precision mediump float; varying vec2 uv; uniform sampler2D t;
void main() {
  vec3 c = texture2D(t, vec2(uv.x, uv.y * .5)).rgb;
  float a = texture2D(t, vec2(uv.x, uv.y * .5 + .5)).r;
  gl_FragColor = vec4(c * a, a);
}`

function setupGL(canvas: HTMLCanvasElement) {
  const gl = canvas.getContext('webgl', { premultipliedAlpha: true, alpha: true })
  if (!gl) return null
  const sh = (type: number, src: string) => {
    const s = gl.createShader(type)!
    gl.shaderSource(s, src)
    gl.compileShader(s)
    return s
  }
  const prog = gl.createProgram()!
  gl.attachShader(prog, sh(gl.VERTEX_SHADER, VERT))
  gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, FRAG))
  gl.linkProgram(prog)
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return null
  gl.useProgram(prog)
  gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer())
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW)
  const loc = gl.getAttribLocation(prog, 'p')
  gl.enableVertexAttribArray(loc)
  gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0)
  gl.bindTexture(gl.TEXTURE_2D, gl.createTexture())
  for (const [k, v] of [
    [gl.TEXTURE_MIN_FILTER, gl.LINEAR],
    [gl.TEXTURE_MAG_FILTER, gl.LINEAR],
    [gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE],
    [gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE],
  ])
    gl.texParameteri(gl.TEXTURE_2D, k, v)
  return (video: HTMLVideoElement) => {
    gl.viewport(0, 0, canvas.width, canvas.height)
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, gl.RGB, gl.UNSIGNED_BYTE, video)
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4)
  }
}

/**
 * The hero element: the 3D doodle (modelled, rigged and animated in Blender, see scripts/doodle-3d),
 * shown from the waist up. He waves hi once the preloader has lifted, and again whenever he is
 * clicked. At rest, and with reduced motion, it is a still image of the same render.
 */
export function HeroDoodle() {
  useIntroClock()
  const video = useRef<HTMLVideoElement>(null)
  const canvas = useRef<HTMLCanvasElement>(null)
  const play = useRef<() => void>(() => {})

  useEffect(() => {
    const v = video.current
    const c = canvas.current
    if (!v || !c) return
    let draw: ReturnType<typeof setupGL> = null
    let raf = 0
    const loop = () => {
      draw?.(v)
      if (!v.paused && !v.ended) raf = requestAnimationFrame(loop)
      else c.style.opacity = '0' // the last frame is the rest pose: hand back to the still
    }
    play.current = () => {
      if (isReduced()) return
      draw ??= setupGL(c)
      if (!draw) return
      v.currentTime = 0
      v.play()
        .then(() => {
          c.style.opacity = '1'
          cancelAnimationFrame(raf)
          raf = requestAnimationFrame(loop)
        })
        .catch(() => {})
    }
    // fetch the wave only once the page itself has loaded, so it never competes with first paint
    const fetchWave = () => {
      if (!isReduced()) {
        v.preload = 'auto'
        v.load()
      }
    }
    if (document.readyState === 'complete') fetchWave()
    else window.addEventListener('load', fetchWave, { once: true })
    const id = setTimeout(() => play.current(), document.documentElement.classList.contains('no-intro') ? 400 : INTRO_MS + 700)
    return () => {
      window.removeEventListener('load', fetchWave)
      clearTimeout(id)
      cancelAnimationFrame(raf)
    }
  }, [])

  return (
    <div className="relative flex justify-center">
      <button
        type="button"
        onClick={() => play.current()}
        aria-label="Say hi to the doodle"
        data-cursor="Say hi"
        className="doodle-bust relative block aspect-[720/664] h-[36svh] tab:h-[46svh] desk:h-[min(68svh,46rem)]"
      >
        <img
          src="/doodle3d/rest.webp"
          alt="Doodle of Abhyuday, in 3D"
          width={720}
          height={664}
          fetchPriority="high"
          className="absolute inset-0 h-full w-full"
        />
        <canvas
          ref={canvas}
          width={720}
          height={664}
          aria-hidden
          className="absolute inset-0 h-full w-full opacity-0"
        />
        <video ref={video} muted playsInline preload="none" aria-hidden className="hidden">
          <source src="/doodle3d/wave.mp4" type="video/mp4" />
          <source src="/doodle3d/wave.webm" type="video/webm" />
        </video>
      </button>
    </div>
  )
}
