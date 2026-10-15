# Builds the preloader film: the doodle walks in from the right pushing the m/ logo until it sits in the
# centre of the screen, then straightens up and hops.
#
# The upper body (torso, arms, head) is traced from the pushing drawing by push.py (upper.svg). The legs
# are drawn here as vector parts (thigh, shin, shoe with round joints, outlined as one shape) so they can
# really walk: each frame, the hips move along a speed curve, every foot is planted on the ground while
# the body passes over it (heel lifting as it pushes off), then swings forward in an arc and lands
# heel first; a two-bone IK solver finds the hip and knee angles. Frames are sampled at 30 fps into CSS
# keyframes, so the result is a self-contained animated SVG that plays like a video at any size.
#
# Writes four cuts into the output directory: wide-light, wide-dark, tall-light, tall-dark.
#   (in a scratch dir) python3 <repo>/scripts/doodle-trace/push.py
#                      python3 <repo>/scripts/doodle-trace/walk.py <repo>/public/preloader
import json, math, os, sys

meta = json.load(open('rig.json'))
upper_svg = open('upper.svg').read()
out_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
os.makedirs(out_dir, exist_ok=True)
R = meta['rel']
FILL = meta['fills']
k = meta['scale']  # world units per original drawing pixel (the traced upper body's units)

# ---------------- the stage (scene units; wide stage 1600 x 1000) ----------------
GROUND = 780
LOGO_W_SCENE = 700
F = 412 / 1311  # world -> scene (figure about 412 scene units tall)
u = LOGO_W_SCENE / 1.98 / F  # one logo unit, in world units
LOGO_FINAL_X = (800 - LOGO_W_SCENE / 2) / F  # world x of the logo's left edge when it is centred
LOGO_START_X = 1290 / F  # starts with only its left edge on screen

# ---------------- the legs (world units) ----------------
L1, L2 = 76 * k, 78 * k  # thigh, shin
REACH = 0.985 * (L1 + L2)
ANKLE_H = 20 * k  # ankle height above the ground when the foot is flat
TOE = (-44 * k, ANKLE_H)  # toe tip relative to the ankle (the foot points forward = left)
HEEL = (14 * k, ANKLE_H)
W_THIGH, W_KNEE, W_ANKLE = 44 * k, 36 * k, 31 * k
LINE = 3.4 * k  # outline width, matching the traced drawing
HIP_H = 482  # walking hip height (a slight crouch: he is pushing)
HIPS = {'f': (R['front_hip'][0], R['front_hip'][1]), 'b': (R['back_hip'][0], R['back_hip'][1])}

# Hands on the slash: the upper hand rests on the slash's edge, the lower one presses on its face.
back_hand_h = HIP_H - R['back_hand'][1]  # height above the ground (y down, so subtract)
HAND_TO_LOGO = R['back_hand'][0] - (1.62 + 0.36 * back_hand_h / u) * u - 12  # logo_x = hip_x + this


def capsule(l, w0, w1):
    """Tapered limb with round ends, pivot at the top, pointing down."""
    a, b = w0 / 2, w1 / 2
    return f'M{-a:.1f} 0L{-b:.1f} {l:.1f}A{b:.1f} {b:.1f} 0 0 0 {b:.1f} {l:.1f}L{a:.1f} 0A{a:.1f} {a:.1f} 0 0 0 {-a:.1f} 0Z'


SHOE = ('M{0} {1}C{2} {3} {4} {5} {6} {7}L{8} {9}C{10} {11} {12} {13} {14} {15}C{16} {17} {18} {19} {20} {21}Z'
        .format(*[round(v * k, 1) for v in (12, -9, 17, 1, 17, 14, 13, 20, -37, 20, -47, 20, -49, 9, -41, 4, -30, -2, -14, -5, -8, -11)]))


def leg(side, layer):
    """One leg as nested groups (thigh > shin > foot). layer 'line' draws the outline (thick stroke, so the
    parts read as one shape), layer 'fill' the colours and details on top."""
    pants = FILL['slate'] if side == 'f' else '#545e64'  # the far leg a touch darker
    shoe = '#47515a' if side == 'f' else '#3e474f'
    hx, hy = HIPS[side]
    if layer == 'line':
        st = f'fill="{FILL["ink"]}" stroke="{FILL["ink"]}" stroke-width="{2 * LINE:.0f}" stroke-linejoin="round"'
        th, sh, ft = (f'<path d="{capsule(L1, W_THIGH, W_KNEE)}" {st}/>', f'<path d="{capsule(L2, W_KNEE, W_ANKLE)}" {st}/>',
                      f'<path d="{SHOE}" {st}/>')
    else:
        crease = f'<path d="M{-W_KNEE * 0.45:.0f} {L1 - 26:.0f}q{W_KNEE * 0.3:.0f} {14:.0f} {W_KNEE * 0.62:.0f} 2" fill="none" stroke="{FILL["ink"]}" stroke-width="{LINE * 0.55:.1f}" stroke-linecap="round"/>'
        cuff = f'<path d="M{-W_ANKLE / 2 + 4:.0f} {L2 - 40:.0f}h{W_ANKLE - 8:.0f}" stroke="{FILL["ink"]}" stroke-width="{LINE * 0.5:.1f}" stroke-linecap="round" opacity=".55"/>'
        sole = f'<path d="M{12 * k:.0f} {14 * k:.0f}L{-42 * k:.0f} {15 * k:.0f}" stroke="#7d868c" stroke-width="{2.4 * k:.0f}" stroke-linecap="round"/>'
        th = f'<path d="{capsule(L1, W_THIGH, W_KNEE)}" fill="{pants}"/>{crease}'
        sh = f'<path d="{capsule(L2, W_KNEE, W_ANKLE)}" fill="{pants}"/>{cuff}'
        ft = f'<path d="{SHOE}" fill="{shoe}"/>{sole}'
    return (f'<g transform="translate({hx:.0f} {hy:.0f})"><g class="th{side}">{th}'
            f'<g transform="translate(0 {L1:.0f})"><g class="sh{side}">{sh}'
            f'<g transform="translate(0 {L2:.0f})"><g class="ft{side}">{ft}</g></g></g></g></g></g>')


# ---------------- motion ----------------
FPS = 30
T_START, T_ARRIVE = 0.15, 2.75
STEP = 0.32  # seconds per step
STEP_BACK = 170  # how far he steps back after the logo lands
STANCE = 0.66  # share of a foot's cycle spent on the ground
HIP_START = LOGO_START_X - HAND_TO_LOGO
HIP_END = LOGO_FINAL_X - HAND_TO_LOGO
DIST = HIP_START - HIP_END


def smooth(t):
    t = min(1, max(0, t))
    return t * t * (3 - 2 * t)


def hip_x(t):
    """Speed ramps up, surges a little on every push-off, and eases to a stop exactly on target."""
    if t <= T_START:
        return HIP_START
    if t >= T_ARRIVE:  # lets go and steps back from the logo
        return HIP_END + STEP_BACK * smooth((t - T_ARRIVE - 0.12) / 0.4)
    s = (t - T_START) / (T_ARRIVE - T_START)
    base = s * s * (3 - 2 * s) * 0.5 + s * 0.5  # gentler ease than smoothstep: he never stands still
    surge = 0.012 * math.sin(2 * math.pi * (t - T_START) / STEP) * math.sin(math.pi * s)
    return HIP_START - DIST * min(1, max(0, base + surge))


# Foot schedule: touchdowns alternate every STEP; each foot lands ahead of its hip and stays planted.
AHEAD = 0.06 * (L1 + L2)  # a pushing gait: feet land under the hips and drive far back
plants = {'f': [], 'b': []}  # (touchdown time, liftoff time, ankle x)
t_cycle = 2 * STEP
for side, phase in (('f', 0.0), ('b', 1.0)):
    # initial stance: front foot slightly ahead, back foot behind (the drawing's lunge)
    plants[side].append((-1.0, T_START + phase * STEP + (STANCE * t_cycle - STEP) * 0.3,
                         HIP_START + HIPS[side][0] + (-AHEAD * 0.6 if side == 'f' else 150)))
    t = T_START + phase * STEP + STEP * 0.85
    while t < T_ARRIVE - 0.05:
        lift = t + STANCE * t_cycle
        x = hip_x(t) + HIPS[side][0] - AHEAD
        plants[side].append((t, lift, x))
        t += t_cycle
# After stopping, any foot still out of place takes one last small step to settle under the body.
SETTLE = {'f': HIP_END + STEP_BACK + HIPS['f'][0] - 50, 'b': HIP_END + STEP_BACK + HIPS['b'][0] + 30}
for side, delay in (('b', 0.08), ('f', 0.2)):
    last_td, last_lift, last_x = plants[side][-1]
    td = max(last_lift + 0.22, T_ARRIVE + 0.05 + delay)
    plants[side][-1] = (last_td, min(last_lift, td - 0.22), last_x)
    plants[side].append((td, 99, SETTLE[side]))

T_STAND = T_ARRIVE + 0.42  # straightens up
T_HOP = T_ARRIVE + 0.62  # hops
HOP_LEN = 0.5
DURATION = T_HOP + HOP_LEN + 0.25


def hip_y(t):
    """Height of the hips above the ground: bobs with each step, rises as he straightens, and the hop."""
    h = HIP_H
    if T_START < t < T_ARRIVE + 0.2:
        fade = smooth((t - T_START) / 0.3) * (1 - smooth((t - T_ARRIVE + 0.1) / 0.3))
        h += 14 * math.cos(2 * math.pi * (t - T_START - STEP * 0.85 - STEP / 2) / STEP) * fade
    h += 22 * smooth((t - T_STAND) / 0.3)  # straighter legs
    if T_HOP <= t <= T_HOP + HOP_LEN:
        p = (t - T_HOP) / HOP_LEN
        if p < 0.18:  # crouch
            h -= 40 * math.sin(p / 0.18 * math.pi / 2)
        elif p < 0.78:  # airborne: a parabola
            q = (p - 0.18) / 0.6
            h += -40 * (1 - q) + 200 * 4 * q * (1 - q)
        else:  # land and absorb
            q = (p - 0.78) / 0.22
            h -= 36 * math.sin(q * math.pi)
    return h


def airborne(t):
    if T_HOP <= t <= T_HOP + HOP_LEN:
        p = (t - T_HOP) / HOP_LEN
        return 0.2 < p < 0.76
    return False


def rot(p, a):
    c, s = math.cos(a), math.sin(a)
    return (p[0] * c - p[1] * s, p[0] * s + p[1] * c)


def foot_state(side, t, hx, hy):
    """Ankle position (world, y down, ground at 0) and absolute foot angle (radians, + lifts the toe)."""
    pl = plants[side]
    hip = (hx + HIPS[side][0], hy + HIPS[side][1])
    for i, (td, lo, x) in enumerate(pl):
        if td <= t < lo:  # stance: foot planted; heel lifts once the hip gets too far ahead
            ankle = (x, -ANKLE_H)
            psi = math.radians(10) * (1 - smooth((t - td) / 0.08)) if td > 0 else 0.0
            if math.dist(hip, ankle) > REACH:
                toe = (x + TOE[0], 0)
                lo_a, hi_a = -math.radians(75), 0.0
                for _ in range(30):
                    mid = (lo_a + hi_a) / 2
                    a = (toe[0] - rot(TOE, mid)[0], toe[1] - rot(TOE, mid)[1])
                    if math.dist(hip, a) > REACH:
                        hi_a = mid
                    else:
                        lo_a = mid
                psi = lo_a
                ankle = (toe[0] - rot(TOE, psi)[0], toe[1] - rot(TOE, psi)[1])
            return ankle, psi
        if i + 1 < len(pl) and lo <= t < pl[i + 1][0]:  # swing to the next plant
            nxt = pl[i + 1]
            p = (t - lo) / (nxt[0] - lo)
            a0, psi0 = foot_state_at_lift(side, i)
            e = smooth(p)
            ax = a0[0] + (nxt[2] - a0[0]) * e
            ay = a0[1] + (-ANKLE_H - a0[1]) * e - 30 * k * math.sin(math.pi * min(1, p * 1.05))
            psi = psi0 + (math.radians(10) - psi0) * smooth(p * 1.15)
            return (ax, ay), psi
    return (pl[-1][2], -ANKLE_H), 0.0


_lift_cache = {}


def foot_state_at_lift(side, i):
    key = (side, i)
    if key not in _lift_cache:
        td, lo, x = plants[side][i]
        t = lo - 1e-4
        _lift_cache[key] = foot_state(side, t, hip_x(t), -hip_y(t))
    return _lift_cache[key]


def ik(hip, ankle):
    """Absolute thigh and shin angles (0 = straight down, + = forward/left) for a knee that bends forward."""
    dx, dy = ankle[0] - hip[0], ankle[1] - hip[1]
    d = min(math.hypot(dx, dy), REACH)
    phi = math.atan2(-dx, dy)
    alpha = math.acos(max(-1, min(1, (L1 * L1 + d * d - L2 * L2) / (2 * L1 * d))))
    best = None
    for th in (phi + alpha, phi - alpha):
        knee = (hip[0] - L1 * math.sin(th), hip[1] + L1 * math.cos(th))
        if best is None or knee[0] < best[1][0]:
            best = (th, knee)
    th, knee = best
    sh = math.atan2(-(ankle[0] - knee[0]), ankle[1] - knee[1])
    return th, sh


frames = []
n = int(DURATION * FPS) + 1
for i in range(n):
    t = i / FPS
    hx, hyw = hip_x(t), -hip_y(t)  # world: y down, ground at 0
    f = {'t': t, 'root': (hx, hyw)}
    for side in ('f', 'b'):
        hip = (hx + HIPS[side][0], hyw + HIPS[side][1])
        if airborne(t):
            # tuck: feet hang below the hips, knees bent, toes pointing down a little
            ankle = (hip[0] + (-40 if side == 'f' else 40), hip[1] + REACH * 0.82)
            psi = math.radians(-14)
        else:
            ankle, psi = foot_state(side, t, hx, hyw)
        th, sh = ik(hip, ankle)
        f[side] = (math.degrees(th), math.degrees(sh - th), math.degrees(psi - sh))
    # upper body: leans into each shove, then straightens up at the end; head follows a beat later
    s = (t - T_START) / (T_ARRIVE - T_START)
    pulse = max(0, math.sin(2 * math.pi * (t - T_START) / STEP)) * (1 if 0 < s < 1 else 0)
    stand = smooth((t - T_STAND) / 0.35)
    f['upper'] = -2.2 * pulse + 13 * stand
    pulse_late = max(0, math.sin(2 * math.pi * (t - T_START - 0.07) / STEP)) * (1 if 0 < s < 1 else 0)
    f['head'] = -3 * pulse_late + 7 * smooth((t - T_STAND - 0.08) / 0.35)
    f['arms'] = -16 * stand
    # the logo stays against the hands while pushing, then stops where it is
    lean = math.radians(f['upper'] if t < T_STAND else -2.2 * pulse)
    hand = rot(R['back_hand'], lean)
    lx = hx + hand[0] - R['back_hand'][0] + HAND_TO_LOGO
    f['logo'] = min(max(lx, LOGO_FINAL_X), LOGO_START_X) if t < T_ARRIVE else LOGO_FINAL_X
    frames.append(f)


def keyframes(name, values, fmt):
    rows = []
    for fr, v in zip(frames, values):
        rows.append(f'{fr["t"] / DURATION * 100:.2f}%{{transform:{fmt(v)}}}')
    return f'@keyframes {name}{{{"".join(rows)}}}.{name}{{animation:{name} {DURATION:.2f}s linear both}}'


css = [
    keyframes('wroot', [f['root'] for f in frames], lambda v: f'translate({v[0]:.1f}px,{v[1]:.1f}px)'),
    keyframes('wlogo', [f['logo'] for f in frames], lambda v: f'translate({v:.1f}px,0)'),
    keyframes('wupper', [f['upper'] for f in frames], lambda v: f'rotate({v:.2f}deg)'),
    keyframes('whead', [f['head'] for f in frames], lambda v: f'rotate({v:.2f}deg)'),
    keyframes('warms', [f['arms'] for f in frames], lambda v: f'rotate({v:.2f}deg)'),
]
for side in ('f', 'b'):
    for j, part in enumerate(('th', 'sh', 'ft')):
        css.append(keyframes(f'{part}{side}', [f[side][j] for f in frames], lambda v: f'rotate({v:.1f}deg)'))
# shadow under him follows the hips and shrinks while he is in the air
css.append(keyframes('wshadow', [(f['root'][0], 1 - 0.45 * max(0, (hip_y(f['t']) - HIP_H - 22) / 200)) for f in frames],
                     lambda v: f'translate({v[0]:.1f}px,0) scale({v[1]:.3f},1)'))
css.append(f'''
.wlogo-b{{transform-origin:{LOGO_W_SCENE / F / 2:.0f}px 0;animation:thud .45s cubic-bezier(.3,.7,.4,1) {T_ARRIVE - 0.04:.2f}s both}}
@keyframes thud{{0%,100%{{transform:none}}30%{{transform:scale(1.035,.94)}}65%{{transform:scale(.99,1.02)}}}}
.dust circle{{transform-box:fill-box;transform-origin:center;opacity:0;animation:puff .6s ease-out both}}
@keyframes puff{{0%{{opacity:.5;transform:scale(.3)}}100%{{opacity:0;transform:translate(var(--dx),-60px) scale(1.3)}}}}
@media (prefers-reduced-motion:reduce){{*{{animation-duration:1ms!important;animation-delay:0s!important}}}}
''')
CSS = ''.join(css)


def logo_paths(ink, accent):
    """The m/ mark (same pieces as components/logo/geometry.ts), bottom-left at the origin, y up."""
    def rect(x, y, w, h, r=(0, 0, 0, 0)):
        tl, tr, br, bl = (v * u for v in r)
        X0, X1, Y0, Y1 = x * u, (x + w) * u, -(y + h) * u, -y * u
        d = f'M{X0 + tl:.1f} {Y0:.1f}H{X1 - tr:.1f}'
        d += f'A{tr:.1f} {tr:.1f} 0 0 1 {X1:.1f} {Y0 + tr:.1f}' if tr else ''
        d += f'V{Y1:.1f}H{X0:.1f}V{Y0 + tl:.1f}'
        d += f'A{tl:.1f} {tl:.1f} 0 0 1 {X0 + tl:.1f} {Y0:.1f}' if tl else ''
        return d + 'Z'
    m = ''.join(f'<path d="{d}"/>' for d in [rect(0, 0.72, 1.24, 0.28, (0.28, 0.28, 0, 0)), rect(0, 0, 0.26, 0.74),
                                             rect(0.49, 0, 0.26, 0.74), rect(0.98, 0, 0.26, 0.74)])
    slash = ' '.join(f'{x * u:.1f},{-y * u:.1f}' for x, y in [(1.38, 0), (1.62, 0), (1.98, 1), (1.74, 1)])
    return f'<g fill="{ink}">{m}</g><polygon fill="{accent}" points="{slash}"/>'


def dust(colour):
    """Puffs that stay on the ground: at every push-off (the toe leaving the ground) and where the logo scrapes."""
    out = ''
    for side in ('f', 'b'):
        for td, lo, x in plants[side][:-1]:
            if not (T_START < lo < T_ARRIVE):
                continue
            tx = x + TOE[0]
            for dx, r, dt in ((40, 30, 0), (90, 20, .05), (-20, 16, .08)):
                out += f'<circle cx="{tx + dx:.0f}" cy="{-r:.0f}" r="{r}" style="--dx:{dx * 1.4:.0f}px;animation-delay:{lo + dt:.2f}s"/>'
    for i in range(int((T_ARRIVE - T_START) / STEP)):
        t = T_START + (i + 0.5) * STEP
        x = frames[int(t * FPS)]['logo'] + 1.62 * u
        for dx, r, dt in ((30, 26, 0), (90, 16, .05)):
            out += f'<circle cx="{x + dx:.0f}" cy="{-r:.0f}" r="{r}" style="--dx:{dx * 1.5:.0f}px;animation-delay:{t + dt:.2f}s"/>'
    return f'<g class="dust" fill="{colour}">{out}</g>'


def scene(view, ink, shadow_fill, shadow_op, dust_fill):
    sh = f'fill="{shadow_fill}" opacity="{shadow_op}"'
    sx, sy = R['shoulder']
    nx, ny = R['neck']
    # the traced upper body: arms and head get their own animated wrappers around their pivots
    upper = upper_svg.replace('<g class="r-arms" ', f'<g class="warms" style="transform-origin:{sx + meta["hips"][0]:.0f}px {sy + meta["hips"][1]:.0f}px"><g ', 1)
    upper = upper.replace('<g class="r-head" ', f'<g class="whead" style="transform-origin:{nx + meta["hips"][0]:.0f}px {ny + meta["hips"][1]:.0f}px"><g ', 1)
    # close the two wrappers we opened (each r- group is closed by its own markup, so close ours after it)
    upper = close_after(upper, 'class="warms"')
    upper = close_after(upper, 'class="whead"')
    figure = (f'<g class="wroot">{leg("b", "line")}{leg("b", "fill")}{leg("f", "line")}{leg("f", "fill")}'
              f'<g class="wupper" style="transform-origin:0 0">{upper}</g></g>')
    world = (f'<g transform="translate(0 {GROUND}) scale({F:.5f})">{dust(dust_fill)}'
             f'<g class="wshadow"><ellipse cx="0" cy="8" rx="560" ry="40" {sh}/></g>'
             f'<g class="wlogo"><ellipse cx="{LOGO_W_SCENE / F / 2:.0f}" cy="8" rx="{LOGO_W_SCENE / F * 0.52:.0f}" ry="40" {sh}/>'
             f'<g class="wlogo-b">{logo_paths(ink, "#ff4c24")}</g></g>{figure}</g>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view}" preserveAspectRatio="xMidYMid meet">'
            f'<!-- Generated by scripts/doodle-trace/walk.py --><style>{CSS}</style>{world}</svg>')


def close_after(svg, marker):
    """Find the wrapper opened at `marker` and add a closing tag after the element that follows it."""
    i = svg.index(marker)
    j = svg.index('<g ', i + 1)  # the original group, now nested
    depth, pos = 0, j
    while True:
        a, b = svg.find('<g', pos), svg.find('</g>', pos)
        if a != -1 and a < b:
            depth += 1
            pos = a + 2
        else:
            depth -= 1
            pos = b + 4
            if depth == 0:
                return svg[:pos] + '</g>' + svg[pos:]


themes = {'light': ('#111111', '#1e2a3a', 0.13, '#9aa3a6'), 'dark': ('#ebe9e4', '#000000', 0.5, '#5b6266')}
views = {'wide': '0 0 1600 1000', 'tall': '130 200 1340 1000'}
for vname, view in views.items():
    for tname, (ink, sf, so, df) in themes.items():
        path = os.path.join(out_dir, f'{vname}-{tname}.svg')
        open(path, 'w').write(scene(view, ink, sf, so, df))
        print(path, os.path.getsize(path))
print(f'{n} frames, {DURATION:.2f}s, arrives {T_ARRIVE}s; steps:', {s: len(p) for s, p in plants.items()})
