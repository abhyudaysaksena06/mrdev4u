import { useId } from 'react'

/**
 * The doodle of me: curly hair, glasses, green hoodie. Drawn as one SVG with named parts
 * (head, eyes, arm-l, arm-r, leg-l, leg-r) so each can be animated later. A light "sticker"
 * outline keeps the dark lines readable on the dark theme.
 */
export function Doodle({ className, title = 'Doodle of Abhyuday' }: { className?: string; title?: string }) {
  const id = useId().replace(/:/g, '')
  return (
    <svg viewBox="0 0 160 330" className={className} role="img" aria-label={title}>
      <defs>
        <filter id={`sticker-${id}`} x="-10%" y="-10%" width="120%" height="120%">
          <feMorphology in="SourceAlpha" operator="dilate" radius="3" result="d" />
          <feFlood floodColor="#f6f4ef" />
          <feComposite in2="d" operator="in" result="o" />
          <feMerge>
            <feMergeNode in="o" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <ellipse cx="80" cy="314" rx="46" ry="7" fill="currentColor" opacity=".14" />
      <g filter={`url(#sticker-${id})`} stroke="#1c2533" strokeWidth="3.5" strokeLinejoin="round" strokeLinecap="round">
        <g className="leg-l">
          <path d="M60 204 L59 296 L78 296 L80 212 Z" fill="#2b3442" />
          <path d="M59 293 h19 q3 9 0 15 h-28 q-7 0 -5 -6 q3 -9 14 -9z" fill="#232b38" />
        </g>
        <g className="leg-r">
          <path d="M80 212 L82 296 L101 296 L100 204 Z" fill="#2b3442" />
          <path d="M82 293 h19 q11 0 14 9 q2 6 -5 6 h-28 q-3 -6 0 -15z" fill="#232b38" />
        </g>
        {/* hoodie: hood behind the neck, body, tee, hem, collar, drawstrings */}
        <path d="M56 106 Q54 88 66 85 L94 85 Q106 88 104 106 Z" fill="#255a32" />
        <path d="M50 106 Q80 96 110 106 Q118 110 117 128 L117 206 Q80 212 43 206 L43 128 Q42 110 50 106Z" fill="#2e6b3c" />
        <path d="M66 102 L94 102 L95 209 Q80 211 65 209 Z" fill="#fff" />
        <path d="M71 102 Q80 112 89 102" fill="none" strokeWidth="2.5" />
        <path d="M43 197 L65 199 L65 209 Q54 209 43 206Z" fill="#255a32" />
        <path d="M117 197 L95 199 L95 209 Q106 209 117 206Z" fill="#255a32" />
        <path d="M65 99 Q55 102 57 118 L66 130 Z" fill="#2e6b3c" />
        <path d="M95 99 Q105 102 103 118 L94 130 Z" fill="#2e6b3c" />
        <path d="M69 110 L68 134 M91 110 L92 134" stroke="#f6f4ef" strokeWidth="2.2" />
        <g className="arm-l" transform="rotate(9 50 110)">
          <path d="M41 110 Q50 103 59 112 L57 191 L40 191 Z" fill="#2e6b3c" />
          <path d="M43.5 117 L42 184" stroke="#7ec850" strokeWidth="3" />
          <path d="M39 188 h19 v10 h-19z" fill="#255a32" />
          <path d="M40 198 h17 q4 13 -2 21 q-7 6 -13 0 q-5 -8 -2 -21z" fill="#fdfbf7" />
          <path d="M41 205 q-5 2 -4 8 M47 210 v8 M52 209 v8" fill="none" strokeWidth="2.2" />
        </g>
        <g className="arm-r" transform="rotate(-9 110 110)">
          <path d="M119 110 Q110 103 101 112 L103 191 L120 191 Z" fill="#2e6b3c" />
          <path d="M116.5 117 L118 184" stroke="#7ec850" strokeWidth="3" />
          <path d="M102 188 h19 v10 h-19z" fill="#255a32" />
          <path d="M103 198 h17 q3 13 -2 21 q-6 6 -13 0 q-6 -8 -2 -21z" fill="#fdfbf7" />
          <path d="M119 205 q5 2 4 8 M113 210 v8 M108 209 v8" fill="none" strokeWidth="2.2" />
        </g>
        <g className="head">
          <path d="M73 84 h14 v18 h-14z" fill="#fdfbf7" />
          <circle cx="54" cy="64" r="6.5" fill="#fdfbf7" />
          <circle cx="106" cy="64" r="6.5" fill="#fdfbf7" />
          <ellipse cx="80" cy="62" rx="26" ry="29" fill="#fdfbf7" />
          <path
            d="M52 63 C45 55 47 42 56 39 C56 29 68 25 74 30 C79 22 93 23 95 30 C103 26 113 35 109 43 C115 50 113 60 108 63 C105 55 101 50 96 49 C93 54 88 55 85 49 C81 55 74 54 72 48 C68 52 62 51 60 47 C57 52 55 57 52 63 Z"
            fill="#1c2533"
          />
          <path d="M64 36 q4 -4 8 0 M84 31 q4 -3 8 1 M99 40 q4 -1 5 4 M56 46 q2 -4 6 -3" fill="none" stroke="#3b475a" strokeWidth="2" />
          <rect x="60.5" y="56" width="17" height="13.5" rx="4.5" fill="#fff" fillOpacity=".4" />
          <rect x="82.5" y="56" width="17" height="13.5" rx="4.5" fill="#fff" fillOpacity=".4" />
          <path d="M77.5 61 q2.5 -2 5 0 M60.5 60 L54 58.5 M99.5 60 L106 58.5" fill="none" strokeWidth="3" />
          <g className="eyes" fill="#1c2533" stroke="none">
            <circle cx="69" cy="63" r="2.4" />
            <circle cx="91" cy="63" r="2.4" />
          </g>
          <path d="M70 76 q10 10 20 0 z" fill="#fff" strokeWidth="3" />
        </g>
      </g>
    </svg>
  )
}
