# Builds the preloader "film": a self-contained animated SVG in which the doodle (the rig from push.py)
# pushes the m/ logo in from the right, in strides, until it sits in the centre of the screen.
# Everything (walk cycle, shoves, logo, dust) is timed inside one file, so nothing can drift apart.
#
# Writes four variants into public/preloader/: wide-light, wide-dark, tall-light, tall-dark.
# The page shows the one that fits the screen and theme as a background image.
#   python3 <repo>/scripts/doodle-trace/push.py           (in a scratch dir: writes rig.svg, rig.json)
#   python3 <repo>/scripts/doodle-trace/scene.py <repo>/public/preloader
import json, os, sys

rig = open('rig.svg').read()
meta = json.load(open('rig.json'))
out_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
os.makedirs(out_dir, exist_ok=True)

# ---- layout (scene units; the wide stage is 1600 x 1000) ----
GROUND = 780
LOGO_W = 700
u = LOGO_W / 1.98  # one logo unit
LOGO_X = 800 - LOGO_W / 2  # logo ends centred
F = 412 / 1311  # rig units -> scene units (figure about 412 tall)
# Hands rest on the slash: put the upper hand on its edge (the lower one presses on its face).
back_h = (meta['ground'] - meta['back_hand'][1]) * F
edge_x = LOGO_X + (1.62 + 0.36 * back_h / u) * u
RIG_X = edge_x - meta['back_hand'][0] * F + 4
RIG_Y = GROUND - meta['ground'] * F


def logo_paths(ink, accent):
    """The m/ mark (same pieces as components/logo/geometry.ts), bottom-left at the origin, y up."""
    def rect(x, y, w, h, r=(0, 0, 0, 0)):
        tl, tr, br, bl = r
        X0, X1, Y0, Y1 = x * u, (x + w) * u, -(y + h) * u, -y * u
        tl, tr, br, bl = tl * u, tr * u, br * u, bl * u
        d = f'M{X0 + tl:.1f} {Y0:.1f}H{X1 - tr:.1f}'
        d += f'A{tr:.1f} {tr:.1f} 0 0 1 {X1:.1f} {Y0 + tr:.1f}' if tr else ''
        d += f'V{Y1:.1f}H{X0:.1f}V{Y0 + tl:.1f}'
        d += f'A{tl:.1f} {tl:.1f} 0 0 1 {X0 + tl:.1f} {Y0:.1f}' if tl else ''
        return d + 'Z'
    m = ''.join(f'<path d="{d}"/>' for d in [rect(0, 0.72, 1.24, 0.28, (0.28, 0.28, 0, 0)), rect(0, 0, 0.26, 0.74),
                                             rect(0.49, 0, 0.26, 0.74), rect(0.98, 0, 0.26, 0.74)])
    slash = ' '.join(f'{x * u:.1f},{-y * u:.1f}' for x, y in [(1.38, 0), (1.62, 0), (1.98, 1), (1.74, 1)])
    return f'<g fill="{ink}">{m}</g><polygon fill="{accent}" points="{slash}"/>'


# ---- timeline (seconds from when the image loads) ----
T0, N, D = 0.25, 5, 0.46  # start, strides, seconds per stride
END = T0 + N * D  # the last stride lands here (2.55 s)
X0 = 1300  # how far right everything starts
STEP = X0 / N


def travel_keyframes():
    """Each stride: a hard shove (eased out), then a short glide; the last one overshoots a touch."""
    total = END + 0.3
    pct = lambda t: f'{t / total * 100:.3f}%'
    k = [f'0%,{pct(T0)}{{transform:translate({X0}px,0);animation-timing-function:cubic-bezier(.2,.7,.3,1)}}']
    for i in range(N):
        t = T0 + i * D
        x_end = X0 - STEP * (i + 1)
        k.append(f'{pct(t + D * 0.62)}{{transform:translate({x_end - (8 if i == N - 1 else 0):.1f}px,0);animation-timing-function:ease-in-out}}')
        k.append(f'{pct(t + D)}{{transform:translate({x_end:.1f}px,0);animation-timing-function:cubic-bezier(.2,.7,.3,1)}}')
    k.append('100%{transform:translate(0,0)}')
    return f'@keyframes travel{{{"".join(k)}}}', total


travel, TRAVEL_T = travel_keyframes()

# per-stride cycles: front leg steps in the first half, the back leg drags up in the second
cycle = f'animation:{{name}} {D}s ease-in-out {T0}s {N} both'
CSS = travel + '''
.mover{animation:travel %(TRAVEL_T).2fs linear both}
.r-thigh-front{%(c)s}.r-shin-front{%(c2)s}.r-thigh-back{%(c3)s}.r-shin-back{%(c4)s}
.r-upper{%(c5)s}.r-arms{%(c6)s}.r-head{%(c7)s}.r-body{%(c8)s}.logo{%(c9)s}
@keyframes ft{0%%,55%%,100%%{transform:none}25%%{transform:rotate(13deg)}}
@keyframes fs{0%%,55%%,100%%{transform:none}25%%{transform:rotate(-24deg)}}
@keyframes bt{0%%,45%%,100%%{transform:none}75%%{transform:rotate(11deg)}}
@keyframes bs{0%%,45%%,100%%{transform:none}75%%{transform:rotate(-16deg)}}
@keyframes up{0%%,100%%{transform:none}18%%{transform:rotate(-3.5deg)}60%%{transform:rotate(.5deg)}}
@keyframes ar{0%%,100%%{transform:none}18%%{transform:translate(-16px,2px) rotate(-2deg)}55%%{transform:translate(3px,0)}}
@keyframes hd{0%%,100%%{transform:none}18%%{transform:translate(-4px,6px) rotate(-4deg)}60%%{transform:rotate(1deg)}}
@keyframes bd{0%%,50%%,100%%{transform:none}25%%{transform:translateY(-22px)}75%%{transform:translateY(-14px)}}
@keyframes lg{0%%,100%%{transform:none}20%%{transform:rotate(-1.4deg)}45%%{transform:rotate(.4deg)}}
''' % {
    'TRAVEL_T': TRAVEL_T,
    'c': cycle.format(name='ft'), 'c2': cycle.format(name='fs'), 'c3': cycle.format(name='bt'), 'c4': cycle.format(name='bs'),
    'c5': cycle.format(name='up'), 'c6': cycle.format(name='ar'), 'c7': cycle.format(name='hd'), 'c8': cycle.format(name='bd'),
    'c9': cycle.format(name='lg'),
}
# the ending: the logo lands with a thud, he straightens up, looks up, and gives a little hop
CSS += f'''
.logo-b{{transform-origin:{LOGO_W / 2:.0f}px 0;animation:thud .45s cubic-bezier(.3,.7,.4,1) {END - 0.05:.2f}s both}}
@keyframes thud{{0%,100%{{transform:none}}30%{{transform:scale(1.04,.93)}}65%{{transform:scale(.99,1.02)}}}}
.r-upper-b{{animation:stand .5s cubic-bezier(.3,.7,.4,1) {END + 0.1:.2f}s both}}
@keyframes stand{{to{{transform:rotate(5deg)}}}}
.r-arms-b{{animation:release .4s ease-out {END + 0.1:.2f}s both}}
@keyframes release{{to{{transform:translate(18px,4px) rotate(3deg)}}}}
.r-head-b{{animation:proud .5s cubic-bezier(.3,.7,.4,1) {END + 0.2:.2f}s both}}
@keyframes proud{{to{{transform:rotate(7deg) translateY(-4px)}}}}
.r-body-b{{animation:hop .55s cubic-bezier(.3,.7,.4,1) {END + 0.45:.2f}s both}}
@keyframes hop{{0%,100%{{transform:none}}40%{{transform:translateY(-60px)}}75%{{transform:translateY(4px)}}}}
.dust circle{{transform-box:fill-box;transform-origin:center;opacity:0;animation:puff .55s ease-out both}}
@keyframes puff{{0%{{opacity:.55;transform:scale(.3)}}100%{{opacity:0;transform:translate(var(--dx),-18px) scale(1.25)}}}}
@media (prefers-reduced-motion:reduce){{*{{animation-duration:1ms!important;animation-delay:0s!important;animation-iteration-count:1!important}}}}
'''


def dust(colour):
    """Puffs left on the ground (they stay put while he moves on): at his back foot and at the
    logo's trailing corner on every shove."""
    out = ''
    for i in range(N):
        t = T0 + i * D + 0.05
        offset = X0 - STEP * i
        foot_x = RIG_X + meta['back_foot'][0] * F + offset
        corner_x = LOGO_X + 1.62 * u + offset
        for j, (x, r, dx, dt) in enumerate([(foot_x + 6, 9, 22, 0), (foot_x + 22, 6, 34, .04), (foot_x - 8, 5, 14, .07),
                                            (corner_x + 4, 8, 26, .02), (corner_x + 20, 5, 36, .06)]):
            out += f'<circle cx="{x:.0f}" cy="{GROUND - r:.0f}" r="{r}" style="--dx:{dx}px;animation-delay:{t + dt:.2f}s"/>'
    return f'<g class="dust" fill="{colour}">{out}</g>'


def scene(view, ink, shadow_fill, shadow_op, dust_fill):
    logo = (f'<g class="logo" style="transform-origin:{LOGO_X:.0f}px {GROUND}px">'
            f'<g transform="translate({LOGO_X:.1f} {GROUND})"><g class="logo-b">{logo_paths(ink, "#ff4c24")}</g></g></g>')
    shadows = (f'<ellipse cx="{LOGO_X + LOGO_W / 2:.0f}" cy="{GROUND + 4}" rx="{LOGO_W * 0.52:.0f}" ry="12" fill="{shadow_fill}" opacity="{shadow_op}"/>'
               f'<ellipse cx="{RIG_X + 760 * F:.0f}" cy="{GROUND + 4}" rx="{190:.0f}" ry="13" fill="{shadow_fill}" opacity="{shadow_op}"/>')
    figure = f'<g transform="translate({RIG_X:.1f} {RIG_Y:.1f}) scale({F:.5f})">{rig}</g>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view}" preserveAspectRatio="xMidYMid meet">'
            f'<!-- Generated by scripts/doodle-trace/scene.py -->'
            f'<style>{CSS}</style>'
            f'{dust(dust_fill)}<g class="mover">{shadows}{logo}{figure}</g></svg>')


themes = {'light': ('#111111', '#1e2a3a', 0.13, '#9aa3a6'), 'dark': ('#ebe9e4', '#000000', 0.5, '#5b6266')}
views = {'wide': '0 0 1600 1000', 'tall': '130 200 1340 1000'}
for vname, view in views.items():
    for tname, (ink, sf, so, df) in themes.items():
        path = os.path.join(out_dir, f'{vname}-{tname}.svg')
        open(path, 'w').write(scene(view, ink, sf, so, df))
        print(path, os.path.getsize(path))
print('rig at', round(RIG_X), round(RIG_Y), 'scale', round(F, 4), 'push ends', round(END, 2), 's')
