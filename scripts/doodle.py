# The doodle drawing. Every part is a base fill, clipped shading, then an outline.
# Usage: python3 scripts/doodle.py preview.svg components/doodle/Doodle.tsx
import sys
INK='#1e2a3a'
C=dict(skin='#fbfaf7', skinSh='#e3e7ec', hair='#243145', hairHi='#3d4e66',
       hood='#2f6a3f', hoodSh='#245535', hoodDeep='#1d4a2d', stripe='#7cc35a',
       tee='#ffffff', teeSh='#e2e7ec', pants='#2c3747', pantsSh='#222b39',
       shoe='#262f3d', sole='#3b4759')
W=5  # outline width
uid=[0]
def part(d, fill, shades=(), sw=W, extra=''):
    uid[0]+=1; cid=f'c{uid[0]}'
    out=[]
    if shades:
        out.append(f'<clipPath id="{cid}"><path d="{d}"/></clipPath>')
    out.append(f'<path d="{d}" fill="{fill}"/>')
    if shades:
        out.append(f'<g clip-path="url(#{cid})">' + ''.join(f'<path d="{s}" fill="{f}"/>' for s,f in shades) + '</g>')
    out.append(extra)
    out.append(f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{sw}"/>')
    return ''.join(out)
def line(d, sw=3.5, col=INK):
    return f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{sw}"/>'

# ---------- legs ----------
def mkLeg():
  return part('M310 584 L388 584 L388 640 L364 828 L314 826 C310 740 308 660 310 584Z', C['pants'],
              [('M372 600 L392 600 L392 830 L352 830 C356 760 366 680 372 600Z', C['pantsSh']),
               ('M300 584 L476 584 L476 604 L300 604Z', C['pantsSh'])]) + line('M332 712 q9 5 18 1', 3) + part('M316 810 L364 812 C374 826 377 846 369 858 L282 858 C260 858 258 836 276 826 C290 818 304 816 316 810Z', C['shoe'],
               [('M250 846 L384 846 L384 864 L250 864Z', C['sole'])]) + line('M300 826 q8 -1 14 -9 M308 832 q8 -1 14 -9', 2.6, C['sole'])
# ---------- torso ----------
hoodBack = part('M326 384 C316 344 346 314 388 314 C430 314 460 344 450 384Z', C['hoodDeep'])
jacket = part('M322 374 C344 362 360 360 372 360 L404 360 C416 360 432 362 454 374 C468 382 472 398 470 420 L468 590 C436 600 340 600 308 590 L306 420 C304 398 308 382 322 374Z', C['hood'],
              [('M300 400 C314 420 320 500 320 600 L300 600Z', C['hoodSh']),
               ('M476 400 C462 420 456 500 456 600 L476 600Z', C['hoodSh']),
               ('M290 562 L486 562 L486 604 L290 604Z', C['hoodSh'])]) + line('M308 562 C346 566 430 566 468 562', 4)
tee = part('M358 362 L418 362 L422 590 C402 595 374 595 354 590Z', C['tee'],
           [('M350 360 L366 360 C362 420 362 520 364 600 L350 600Z', C['teeSh']),
            ('M426 360 L410 360 C414 420 414 520 412 600 L426 600Z', C['teeSh'])])
neckline = part('M364 362 C372 388 404 388 412 362Z', C['skin'], [('M360 358 L416 358 L416 372 L360 372Z', C['skinSh'])], sw=4)
lapelL = part('M346 336 C328 350 330 382 344 404 L364 398 C354 378 354 356 368 344Z', C['hood'], [('M340 330 L356 330 L352 410 L336 410Z', C['hoodSh'])])
lapelR = part('M430 336 C448 350 446 382 432 404 L412 398 C422 378 422 356 408 344Z', C['hood'], [('M436 330 L420 330 L424 410 L440 410Z', C['hoodSh'])])
def string(x0, y0, x1, y1):
    return (f'<path d="M{x0} {y0} L{x1} {y1}" stroke="{INK}" stroke-width="7.5"/>'
            f'<path d="M{x0} {y0} L{x1} {y1}" stroke="#ffffff" stroke-width="3"/>'
            f'<rect x="{x1-3.5}" y="{y1}" width="7" height="11" rx="2" fill="#ffffff" stroke="{INK}" stroke-width="2.5"/>')
strings = string(352, 396, 351, 436) + string(424, 396, 425, 436)
# ---------- arm (left, viewer's side); right arm is mirrored ----------
def mkArm():
  sleeve = part('M324 372 C298 370 280 388 274 416 L254 566 L298 572 L308 428 C312 404 318 386 324 372Z', C['hood'],
                [('M300 380 C292 440 288 500 286 600 L310 600 L320 380Z', C['hoodSh'])],
                extra=line('M286 398 C280 430 268 500 262 560', 5.5, C['stripe']))
  cuff = part('M253 560 L299 566 L297 592 L250 588Z', C['hoodSh']) + line('M262 566 L261 588 M274 567 L273 589 M286 568 L285 590', 2, C['hoodDeep'])
  hand = part('M256 586 L294 590 C298 598 304 604 308 614 C311 624 304 630 297 623 L293 617 C295 630 292 646 288 656 C286 663 278 662 278 654 C278 661 269 662 268 654 C266 660 258 659 258 651 C255 655 247 652 248 644 C246 628 249 604 256 586Z',
              C['skin'], [('M240 584 L300 584 L300 600 C286 604 260 602 240 598Z', C['skinSh'])], sw=4.5) + line('M281 633 L279 654 M271 634 L268 654 M261 632 L258 650', 2.8)
  return sleeve + cuff + hand
# ---------- head ----------
neck = part('M366 312 L366 364 Q388 374 410 364 L410 312Z', C['skin'], [('M360 300 L416 300 L416 338 Q388 352 360 338Z', C['skinSh'])], sw=4.5)
earL = part('M338 262 C322 254 312 268 315 284 C318 299 330 306 341 300Z', C['skin'], [], sw=4.5) + line('M330 272 q-7 9 2 19', 3)
earR = part('M438 262 C454 254 464 268 461 284 C458 299 446 306 435 300Z', C['skin'], [], sw=4.5) + line('M446 272 q7 9 -2 19', 3)
face = part('M338 238 C336 206 360 190 388 190 C416 190 440 206 438 238 L438 282 C438 318 414 346 388 346 C362 346 338 318 338 282Z', C['skin'],
            [('M330 226 C350 236 426 236 446 226 L446 246 C420 240 356 240 330 246Z', C['skinSh'])], sw=4.5)
hair = part('M338 268 C324 262 316 250 320 238 C306 230 304 212 316 203 C308 186 320 170 336 171 C338 156 357 149 370 157 C380 145 401 145 411 155 C425 147 445 155 447 170 C463 172 471 190 463 204 C475 215 470 235 456 239 C460 252 452 266 438 268 C440 248 434 234 424 227 C417 236 403 237 397 227 C389 235 376 235 370 225 C362 233 350 233 346 225 C340 237 337 250 338 268Z',
            C['hair'], [], sw=4.5) + line('M330 213 c6 -9 19 -7 21 4 M354 181 c8 -7 19 -3 21 6 M392 167 c9 -6 21 -2 23 8 M429 183 c9 -2 17 6 15 15 M446 214 c3 8 -1 15 -8 17 M322 228 c-3 -6 0 -12 6 -14 M370 200 c6 -6 16 -4 18 4 M408 196 c7 -4 15 0 16 7', 3.2, C['hairHi'])
brows = line('M347 243 q13 -7 27 -2 M402 241 q14 -5 27 2', 4.2)
glasses = (f'<rect x="339" y="248" width="44" height="36" rx="10" fill="#ffffff" fill-opacity=".18" stroke="{INK}" stroke-width="5.5"/>'
           f'<rect x="393" y="248" width="44" height="36" rx="10" fill="#ffffff" fill-opacity=".18" stroke="{INK}" stroke-width="5.5"/>'
           + line('M383 263 Q388 257 393 263 M339 258 L325 254 M437 258 L451 254', 5))
eyes = (f'<g><circle cx="362" cy="267" r="5.2" fill="{INK}"/><circle cx="414" cy="267" r="5.2" fill="{INK}"/>'
        f'<circle cx="360.2" cy="265.2" r="1.6" fill="#fff"/><circle cx="412.2" cy="265.2" r="1.6" fill="#fff"/></g>')
nose = line('M389 280 q-5 9 2 11', 3.4)
mouth = part('M367 301 C376 318 400 318 409 301 C396 306 380 306 367 301Z', '#ffffff', [('M360 312 L416 312 L416 330 L360 330Z', '#e9c9c4')], sw=4)

inner = f"""<ellipse class="doodle-shadow" cx="388" cy="860" rx="148" ry="15"/>
<g data-part="leg-l">{mkLeg()}</g>
<g data-part="leg-r"><g transform="translate(776 0) scale(-1 1)">{mkLeg()}</g></g>
<g data-part="upper">
<g data-part="torso">{hoodBack}{jacket}{tee}{neckline}{lapelL}{lapelR}{strings}</g>
<g data-part="arm-l"><g transform="rotate(5 318 380) translate(8 0)">{mkArm()}</g></g>
<g data-part="arm-r"><g transform="translate(776 0) scale(-1 1) rotate(5 318 380) translate(8 0)">{mkArm()}</g></g>
{neck}
<g data-part="head">
<g data-part="ears">{earL}{earR}</g>
{face}
<g data-part="hair">{hair}</g>
<g data-part="features">{brows}{glasses}{nose}{mouth}<g data-part="pupils"><g class="doodle-blink">{eyes}</g></g></g>
</g>
</g>"""
svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="206 140 364 732"><style>.doodle-shadow{{fill:#1e2a3a;opacity:.14}}</style><g stroke-linejoin="round" stroke-linecap="round">{inner}</g></svg>'
open(sys.argv[1],'w').write(svg)

# ---- TSX ----
import re
j = inner
j = re.sub(r'\bclass="', 'className="', j)
for a,b in [('stroke-width','strokeWidth'),('stroke-linejoin','strokeLinejoin'),('stroke-linecap','strokeLinecap'),('fill-opacity','fillOpacity'),('clip-path','clipPath')]:
    j = j.replace(a+'=', b+'=')
j = re.sub(r'id="(c\d+)"', r'id={`${u}\1`}', j)
j = re.sub(r'clipPath="url\(#(c\d+)\)"', r'clipPath={`url(#${u}\1)`}', j)
j = j.replace('><', '>\n<')
tsx = """// Generated by scripts/doodle.py (python3 scripts/doodle.py preview.svg components/doodle/Doodle.tsx).\n// Edit the drawing there, not this file.
import { useId } from 'react'

/**
 * The doodle of me: curly hair, glasses, green hoodie. One SVG with named parts
 * (data-part: upper, torso, arm-l, arm-r, head, ears, hair, features, pupils) that
 * HeroDoodle moves to follow the cursor.
 */
export function Doodle({ className, title = 'Doodle of Abhyuday' }: { className?: string; title?: string }) {
  const u = useId().replace(/:/g, '')
  return (
    <svg viewBox="206 140 364 732" className={className} role="img" aria-label={title}>
      <g strokeLinejoin="round" strokeLinecap="round">
""" + j + """
      </g>
    </svg>
  )
}
"""
open(sys.argv[2],'w').write(tsx)
