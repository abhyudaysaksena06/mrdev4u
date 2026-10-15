# The preloader film (see docs/ANIMATION_PLAN.md, section 1).
#
# The doodle walks in from the right pushing the m/ logo, which is heavy: it moves in stick-slip surges
# while his body drives forward first and his elbows absorb it. Then: anticipation, one big shove that
# lands the logo dead centre, a stumble from the momentum, a cartoon turn to face the camera and a
# squash-and-stretch hop as the curtain lifts.
#
# Rig: head, torso and hands traced from the pushing drawing (push.py -> parts.json); sleeves and legs
# drawn here as vectors in the same style. Hands and feet are placed where they belong (on the logo,
# on the ground) and two-bone IK bends the elbows and knees. Every frame is computed in Python and
# sampled at 30 fps into CSS keyframes, so the output is one self-contained animated SVG per cut.
#
#   (in a scratch dir) python3 <repo>/scripts/doodle-trace/push.py
#                      python3 <repo>/scripts/doodle-trace/film.py <repo>/public/preloader <repo>/public/doodle.svg
import json, math, os, re, sys

parts = json.load(open('parts.json'))
meta = json.load(open('rig.json'))
out_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
front_svg = open(sys.argv[2] if len(sys.argv) > 2 else 'doodle.svg').read()
os.makedirs(out_dir, exist_ok=True)
R, FILL, k = meta['rel'], meta['fills'], meta['scale']
INK, JACKET, STRIPE, PANTS = FILL['ink'], FILL['green'], FILL['lime'], FILL['slate']
CUFF = '#355a4e'
LINE = 3.4 * k  # outline width of the drawing

# ======================= stage =======================
GROUND = 780  # scene y of the ground (wide stage is 1600 x 1000)
LOGO_W_SCENE = 600
F = 412 / 1311  # world (rig units) -> scene
u = LOGO_W_SCENE / 1.98 / F  # one logo unit in world units
# He pushes the m's left stem (a flat, upright wall), coming in from the left. The physics below is
# written in his own (mirrored) frame, where he faces left and pushes toward -x: there, "logo_x" is
# minus the logo's real left edge. The figure is drawn with scale(-1, 1); the logo is drawn as is.
REAL_END = (800 - LOGO_W_SCENE / 2) / F  # logo left edge when centred (real frame)
REAL_START = 40 / F  # mostly on screen, so he is seen pushing it almost at once
LOGO_END, LOGO_START = -REAL_END, -REAL_START
SHOVE = 260  # how far the last big shove sends it


def face_x(lx, h):
    """x (his frame) of the stem's outer face at height h: straight, rounding off near the top."""
    inset = 0.0
    if h > 0.72 * u:
        r = 0.28 * u
        inset = r - math.sqrt(max(0.0, r * r - (h - 0.72 * u) ** 2))
    return lx - inset


# ======================= helpers =======================
def clamp01(t):
    return min(1.0, max(0.0, t))


def smooth(t):
    t = clamp01(t)
    return t * t * (3 - 2 * t)


def ease_out(t, p=3):
    return 1 - (1 - clamp01(t)) ** p


def ease_in(t, p=2):
    return clamp01(t) ** p


def rot(p, a):
    c, s = math.cos(a), math.sin(a)
    return (p[0] * c - p[1] * s, p[0] * s + p[1] * c)


def add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def ik(root, target, l1, l2, bend):
    """Two-bone IK. Angles are absolute (0 = pointing down, + = clockwise). bend=+1 puts the middle joint
    toward -x of the limb's direction (knees forward for legs), -1 the other way (elbows down for arms)."""
    dx, dy = target[0] - root[0], target[1] - root[1]
    d = max(1e-3, min(math.hypot(dx, dy), (l1 + l2) * 0.999))
    phi = math.atan2(-dx, dy)
    a = math.acos(max(-1, min(1, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d))))
    t1 = phi + a * bend
    mid = (root[0] - l1 * math.sin(t1), root[1] + l1 * math.cos(t1))
    t2 = math.atan2(-(target[0] - mid[0]), target[1] - mid[1])
    return t1, t2, mid


# ======================= choreography =======================
T0 = 0.15
STEPS = [0.44, 0.40, 0.36, 0.34, 0.33, 0.33]  # step durations: heavy start, then a steady push
STEP_T = [T0]
for d in STEPS:
    STEP_T.append(STEP_T[-1] + d)
T_PUSH_END = STEP_T[-1]  # ~2.35
T_ANT = T_PUSH_END  # anticipation (crouch, elbows load)
T_SHOVE = T_ANT + 0.2  # explosive shove
T_STOP = T_SHOVE + 0.2  # logo stops (thud)
T_CATCH = T_STOP + 0.1  # catch step lands
T_RECOVER = T_CATCH + 0.16  # stands up, lets go
T_TURN = T_RECOVER + 0.04  # cartoon turn
T_FRONT = T_TURN + 0.1  # front view fully in
DURATION = T_FRONT + 0.75

LOGO_PRE = LOGO_END + SHOVE  # where the steady push leaves it
PUSH_DIST = LOGO_START - LOGO_PRE


def logo_s(t):
    """Distance the logo has travelled: stick-slip surges, one per step, then the big shove."""
    s = 0.0
    total = sum(STEPS)
    for i, d in enumerate(STEPS):
        t0, share = STEP_T[i], d / total
        # stuck for the first quarter of the step (body loads), then breaks free and slides
        p = (t - (t0 + 0.24 * d)) / (0.62 * d)
        s += PUSH_DIST * share * ease_out(p, 2.6)
    s += SHOVE * ease_out((t - T_SHOVE) / (T_STOP - T_SHOVE + 0.05), 3)
    return s


def logo_x(t):
    return LOGO_START - logo_s(t)


# Body distance travelled: leads the logo (drives forward first), smoothed; overshoots on the shove.
def body_s(t):
    lead = 0.05
    s = sum(logo_s(t + lead + dt) for dt in (-0.04, -0.02, 0, 0.02, 0.04)) / 5  # a little smoothing
    if t > T_ANT:
        s = min(s, logo_s(T_ANT + lead))
        s += 60 * smooth((t - T_ANT) / 0.2)  # anticipation: body loads in toward the logo
    if t > T_SHOVE:
        s += (SHOVE + 28) * ease_out((t - T_SHOVE) / 0.24, 2.4)  # momentum carries him a little past
    if t > T_STOP + 0.04:
        s -= 90 * smooth((t - T_STOP - 0.04) / 0.32)  # catches himself and steps back
    return s


HIP_H = 482
# Rest offset: logo edge to pelvis, such that the near arm is slightly bent.
L_NU, L_NF = 262.0, 256.0  # near arm: upper, forearm
L_FU, L_FF = 165.0, 150.0  # far arm (foreshortened, mostly hidden)
HAND_TILT = 0.0  # the drawing's palms are already flat against an upright wall
NEAR_H, FAR_H = 0.6 * u, 0.84 * u  # where his palms press on the stem


def solve_offset():
    """Pelvis x relative to the logo's left edge that leaves the near arm almost straight (97.5% of its reach)."""
    # search only where his shoulder is to the right of his hand (the other solution reaches backwards)
    lo = face_x(0, NEAR_H) - R['near_shoulder'][0] + 20
    hi = lo + 3000
    for _ in range(60):
        mid = (lo + hi) / 2
        sh = (mid + R['near_shoulder'][0], -HIP_H + R['near_shoulder'][1])
        palm = (face_x(0, NEAR_H) + 4, -NEAR_H)
        wrist = add(palm, (-rot(meta['palm']['near'], HAND_TILT)[0], -rot(meta['palm']['near'], HAND_TILT)[1]))
        d = math.dist(sh, wrist)
        if d > 0.975 * (L_NU + L_NF):
            hi = mid
        else:
            lo = mid
    return lo


D0 = solve_offset()
ROOT_START = LOGO_START + D0


def root_x(t):
    return ROOT_START - body_s(t)


def hip_h(t):
    h = HIP_H
    for i, d in enumerate(STEPS):  # bob: dips after each touchdown, rises mid-step
        p = (t - STEP_T[i]) / d
        if 0 <= p < 1:
            h += 7 * math.cos(2 * math.pi * p) - 5  # high as the step begins, lowest mid-stride
    h -= 30 * smooth((t - T_ANT) / 0.18) * (1 - smooth((t - T_SHOVE) / 0.12))  # crouch before the shove
    h -= 18 * smooth((t - T_SHOVE) / 0.1) * (1 - smooth((t - T_CATCH) / 0.16))  # lunge low
    h += 26 * smooth((t - T_CATCH) / 0.2)  # stands up
    return h


def surge(t):
    """0..1 how hard he is straining right now (peaks while the logo breaks free)."""
    v = 0.0
    for i, d in enumerate(STEPS):
        p = (t - STEP_T[i] - 0.18 * d) / (0.6 * d)
        if 0 < p < 1:
            v = max(v, math.sin(math.pi * p))
    if T_ANT < t < T_STOP:
        v = max(v, smooth((t - T_ANT) / 0.15))
    return v


def torso_angle(t):
    a = -2.5 - 3.5 * surge(t)
    a -= 4 * smooth((t - T_ANT) / 0.18) * (1 - smooth((t - T_SHOVE) / 0.1))  # coils
    a -= 5 * smooth((t - T_SHOVE) / 0.14) * (1 - smooth((t - T_CATCH) / 0.18))  # pitches forward
    a += 14 * smooth((t - T_CATCH) / 0.22)  # straightens up
    return a


_head_state = {}


def head_angle(t):
    """Head: follows the torso a beat later (spring), trembles when straining, looks down when pushing."""
    target = lambda tt: -3 * surge(tt) - 4 * smooth((tt - T_ANT) / 0.2) * (1 - smooth((tt - T_CATCH) / 0.2)) + 8 * smooth((tt - T_CATCH - 0.05) / 0.25)
    lagged = target(t - 0.07)
    tremble = 0.9 * surge(t) * math.sin(2 * math.pi * 13 * t)
    whip = -6 * math.exp(-max(0, t - T_STOP) * 14) * math.sin(max(0, t - T_STOP) * 26) if t > T_STOP else 0
    return lagged + tremble + whip + (torso_angle(t - 0.06) - torso_angle(t)) * 0.8


def breath(t):
    return 1 + 0.014 * math.sin(2 * math.pi * 2.1 * t) + 0.02 * math.exp(-max(0, t - T_RECOVER) * 6) * (t > T_RECOVER)


# ----- feet -----
L1, L2 = 76 * k, 78 * k
REACH = 0.985 * (L1 + L2)
ANKLE_H = 20 * k
TOE = (-44 * k, ANKLE_H)
HIPS = {'f': tuple(R['front_hip']), 'b': tuple(R['back_hip'])}
AHEAD = 0.06 * (L1 + L2)
plants = {'f': [], 'b': []}  # (touchdown, liftoff, ankle x)
plants['f'].append((-1, STEP_T[0] + 0.02, ROOT_START + HIPS['f'][0] - AHEAD * 0.5))
plants['b'].append((-1, STEP_T[1] + 0.06, ROOT_START + HIPS['b'][0] + 170))
for i in range(len(STEPS)):
    side = 'f' if i % 2 == 0 else 'b'
    td = STEP_T[i] + STEPS[i] * 0.55
    nxt = STEP_T[i + 2] + STEPS[min(i + 2, len(STEPS) - 1)] * 0.55 - 0.2 if i + 2 < len(STEPS) else T_SHOVE + 0.04
    plants[side].append((td, nxt, root_x(td) + HIPS[side][0] - AHEAD))
# the catch step: the back foot comes through after the shove; the front foot settles after it
last_b = plants['b'][-1]
plants['b'][-1] = (last_b[0], T_SHOVE + 0.06, last_b[2])
plants['b'].append((T_CATCH, 99, root_x(T_CATCH + 0.3) + HIPS['b'][0] - 200))
last_f = plants['f'][-1]
plants['f'][-1] = (last_f[0], T_CATCH + 0.04, last_f[2])
plants['f'].append((T_CATCH + 0.2, 99, root_x(T_CATCH + 0.4) + HIPS['f'][0] - 40))


def foot(side, t, hip):
    pl = plants[side]
    for i, (td, lo, x) in enumerate(pl):
        if td <= t < lo:
            ankle = (x, -ANKLE_H)
            psi = math.radians(10) * (1 - smooth((t - td) / 0.08)) if td > 0 else 0.0
            if math.dist(hip, ankle) > REACH:  # heel lifts: roll over the toe
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
        if i + 1 < len(pl) and lo <= t < pl[i + 1][0]:
            nx = pl[i + 1]
            p = (t - lo) / max(1e-3, nx[0] - lo)
            a0, psi0 = lift_state(side, i)
            e = smooth(p)
            ax = a0[0] + (nx[2] - a0[0]) * e
            ay = a0[1] + (-ANKLE_H - a0[1]) * e - 32 * k * math.sin(math.pi * min(1, p * 1.05))
            psi = psi0 + (math.radians(12) - psi0) * smooth(p * 1.15)
            return (ax, ay), psi
    return (pl[-1][2], -ANKLE_H), 0.0


_lift = {}


def lift_state(side, i):
    if (side, i) not in _lift:
        lo = plants[side][i][1] - 1e-4
        rx, rh = root_x(lo), hip_h(lo)
        _lift[(side, i)] = foot(side, lo, (rx + HIPS[side][0], -rh + HIPS[side][1]))
    return _lift[(side, i)]


# ----- hands -----
def hands(t, lx, root, ta):
    """Wrist targets and absolute hand angles. On the logo while pushing; let go and relax at the end."""
    out = {}
    release = smooth((t - (T_CATCH + 0.06)) / 0.18)
    for side, h, L in (('near', NEAR_H, (L_NU, L_NF)), ('far', FAR_H, (L_FU, L_FF))):
        palm_vec = rot(meta['palm'][side], HAND_TILT)
        palm = (face_x(lx, h) + 4, -h)
        on_logo = add(palm, (-palm_vec[0], -palm_vec[1]))
        sh = add(root, rot(R[f'{side}_shoulder'], math.radians(ta)))
        # relaxed: hands drop to chest height in front of him, palms turning down
        relaxed = add(sh, rot((-0.62 * (L[0] + L[1]), 0.28 * (L[0] + L[1])), 0))
        wrist = (on_logo[0] + (relaxed[0] - on_logo[0]) * release, on_logo[1] + (relaxed[1] - on_logo[1]) * release)
        angle = HAND_TILT * (1 - release) + math.radians(-35) * release
        out[side] = (sh, wrist, angle)
    return out


# ======================= drawing =======================
def capsule(l, w0, w1):
    a, b = w0 / 2, w1 / 2
    return f'M{-a:.1f} 0L{-b:.1f} {l:.1f}A{b:.1f} {b:.1f} 0 0 0 {b:.1f} {l:.1f}L{a:.1f} 0A{a:.1f} {a:.1f} 0 0 0 {-a:.1f} 0Z'


SHOE = ('M{0} {1}C{2} {3} {4} {5} {6} {7}L{8} {9}C{10} {11} {12} {13} {14} {15}C{16} {17} {18} {19} {20} {21}Z'
        .format(*[round(v * k, 1) for v in (12, -9, 17, 1, 17, 14, 13, 20, -37, 20, -47, 20, -49, 9, -41, 4, -30, -2, -14, -5, -8, -11)]))
W_THIGH, W_KNEE, W_ANKLE = 44 * k, 36 * k, 31 * k


def leg(side, layer):
    pants = PANTS if side == 'f' else '#545e64'
    shoe = '#47515a' if side == 'f' else '#3e474f'
    hx, hy = HIPS[side]
    if layer == 'line':
        st = f'fill="{INK}" stroke="{INK}" stroke-width="{2 * LINE:.0f}" stroke-linejoin="round"'
        th, sh, ft = (f'<path d="{capsule(L1, W_THIGH, W_KNEE)}" {st}/>', f'<path d="{capsule(L2, W_KNEE, W_ANKLE)}" {st}/>', f'<path d="{SHOE}" {st}/>')
    else:
        crease = f'<path d="M{-W_KNEE * 0.45:.0f} {L1 - 26:.0f}q{W_KNEE * 0.3:.0f} 14 {W_KNEE * 0.62:.0f} 2" fill="none" stroke="{INK}" stroke-width="{LINE * 0.55:.1f}" stroke-linecap="round"/>'
        cuff = f'<path d="M{-W_ANKLE / 2 + 4:.0f} {L2 - 40:.0f}h{W_ANKLE - 8:.0f}" stroke="{INK}" stroke-width="{LINE * 0.5:.1f}" stroke-linecap="round" opacity=".55"/>'
        sole = f'<path d="M{12 * k:.0f} {14 * k:.0f}L{-42 * k:.0f} {15 * k:.0f}" stroke="#7d868c" stroke-width="{2.4 * k:.0f}" stroke-linecap="round"/>'
        th = f'<path d="{capsule(L1, W_THIGH, W_KNEE)}" fill="{pants}"/>{crease}'
        sh = f'<path d="{capsule(L2, W_KNEE, W_ANKLE)}" fill="{pants}"/>{cuff}'
        ft = f'<path d="{SHOE}" fill="{shoe}"/>{sole}'
    return (f'<g transform="translate({hx:.0f} {hy:.0f})"><g class="th{side}">{th}'
            f'<g transform="translate(0 {L1:.0f})"><g class="sh{side}">{sh}'
            f'<g transform="translate(0 {L2:.0f})"><g class="ft{side}">{ft}</g></g></g></g></g></g>')


def arm(side):
    """Sleeve (upper arm + forearm with the lime stripe and a cuff) and the traced hand, as nested groups."""
    lu, lf = (L_NU, L_NF) if side == 'near' else (L_FU, L_FF)
    w0, w1, w2 = ((40 * k, 34 * k, 31 * k) if side == 'near' else (32 * k, 28 * k, 26 * k))
    jacket = JACKET if side == 'near' else '#3a5f54'
    sx, sy = R[f'{side}_shoulder']
    st = f'fill="{INK}" stroke="{INK}" stroke-width="{2 * LINE:.0f}" stroke-linejoin="round"'
    up_d, fo_d = capsule(lu, w0, w1), capsule(lf - 12, w1, w2)
    cuff_d = f'M{-w2 / 2 - 4:.0f} {lf - 46:.0f}H{w2 / 2 + 4:.0f}V{lf + 14:.0f}H{-w2 / 2 - 4:.0f}Z'
    stripe = lambda l, w: f'<path d="M{-w / 2 + 8:.0f} 14L{-w / 2 + 9:.0f} {l - 10:.0f}" stroke="{STRIPE}" stroke-width="{2.6 * k:.0f}" stroke-linecap="round"/>'
    hand = parts[f'hand_{side}']
    # outline layer, then the hand, then the sleeve colours on top (the cuff covers the wrist cut)
    line = (f'<g class="{side[0]}u"><path d="{up_d}" {st}/><g transform="translate(0 {lu:.0f})"><g class="{side[0]}f">'
            f'<path d="{fo_d}" {st}/><path d="{cuff_d}" {st}/></g></g></g>')
    fill = (f'<g class="{side[0]}u"><path d="{up_d}" fill="{jacket}"/>{stripe(lu, w0)}'
            f'<g transform="translate(0 {lu:.0f})"><g class="{side[0]}f"><g transform="translate(0 {lf:.0f})"><g class="{side[0]}h">{hand}</g></g>'
            f'<path d="{fo_d}" fill="{jacket}"/>{stripe(lf - 30, w1)}'
            f'<path d="{cuff_d}" fill="{CUFF}"/><path d="M{-w2 / 2 - 2:.0f} {lf - 46:.0f}H{w2 / 2 + 2:.0f}" stroke="{INK}" stroke-width="{LINE * 0.6:.1f}"/>'
            f'<path d="M{-w2 / 2 - 4:.0f} {lf + 14:.0f}H{w2 / 2 + 4:.0f}" stroke="{INK}" stroke-width="{LINE:.1f}" stroke-linecap="round"/>'
            f'<path d="M{-w1 * 0.3:.0f} -6q{w1 * 0.25:.0f} 10 {w1 * 0.55:.0f} 0" fill="none" stroke="{INK}" stroke-width="{LINE * 0.5:.1f}" stroke-linecap="round"/>'
            f'</g></g></g>')
    return f'<g transform="translate({sx:.0f} {sy:.0f})">{line}{fill}</g>'


# ======================= simulate =======================
FPS = 30
frames = []
for i in range(int(DURATION * FPS) + 1):
    t = i / FPS
    lx = logo_x(t)
    rx, rh = root_x(t), hip_h(t)
    root = (rx, -rh)
    ta = torso_angle(t)
    fr = {'t': t, 'logo': lx, 'root': root, 'torso': (ta, breath(t)), 'head': head_angle(t)}
    for side in ('f', 'b'):
        hip = add(root, HIPS[side])
        ankle, psi = foot(side, t, hip)
        th, sh, _ = ik(hip, ankle, L1, L2, +1)
        fr[side] = (math.degrees(th), math.degrees(sh - th), math.degrees(psi - sh))
    for side, (sh, wrist, ang) in hands(t, lx, root, ta).items():
        lu, lf = (L_NU, L_NF) if side == 'near' else (L_FU, L_FF)
        t1, t2, _ = ik(sh, wrist, lu, lf, -1)  # elbows bend downward
        tor = math.radians(ta)
        fr[side] = (math.degrees(t1 - tor), math.degrees(t2 - t1), math.degrees(ang - t2))
    frames.append(fr)


def track(name, values, fmt, extra=''):
    rows, last = [], None
    for idx, (fr, v) in enumerate(zip(frames, values)):
        s = fmt(v)
        if s == last and idx not in (len(frames) - 1,) and values[min(idx + 1, len(values) - 1)] == v:
            continue  # drop repeats inside holds (CSS interpolates across them)
        rows.append(f'{fr["t"] / DURATION * 100:.2f}%{{transform:{s}}}')
        last = s
    return f'@keyframes {name}{{{"".join(rows)}}}.{name}{{animation:{name} {DURATION:.2f}s linear both{extra}}}'


deg = lambda v: f'rotate({v:.1f}deg)'
css = [
    track('kroot', [f['root'] for f in frames], lambda v: f'translate({v[0]:.0f}px,{v[1]:.0f}px)'),
    track('klogo', [f['logo'] for f in frames], lambda v: f'translate({-v:.0f}px,0)'),
    track('ktorso', [f['torso'] for f in frames], lambda v: f'rotate({v[0]:.2f}deg) scale(1,{v[1]:.3f})'),
    track('khead', [f['head'] for f in frames], lambda v: f'rotate({v:.2f}deg)'),
    track('kshadow', [f['root'][0] for f in frames], lambda v: f'translate({v:.0f}px,0)'),
]
for side in ('f', 'b'):
    for j, part in enumerate(('th', 'sh', 'ft')):
        css.append(track(f'{part}{side}', [f[side][j] for f in frames], deg))
for side in ('near', 'far'):
    for j, part in enumerate(('u', 'f', 'h')):
        css.append(track(f'{side[0]}{part}', [f[side][j] for f in frames], deg))

X_END = root_x(T_TURN)  # where he stands for the turn
FRONT_SCALE = 408 / 555  # match head sizes: pushing head ~408 world units, front-view head ~555 svg units
css.append(f'''
.klogo-b{{transform-origin:{LOGO_W_SCENE / F / 2:.0f}px 0;animation:thud .5s cubic-bezier(.3,.7,.4,1) {T_STOP - 0.02:.2f}s both}}
@keyframes thud{{0%,100%{{transform:none}}25%{{transform:scale(1.04,.92)}}55%{{transform:scale(.985,1.025)}}80%{{transform:scale(1.005,.995)}}}}
.side{{transform-origin:{X_END:.0f}px 0;animation:turnout .08s ease-in {T_TURN:.2f}s both}}
@keyframes turnout{{to{{transform:scale(.08,1.04);opacity:0}}}}
.front{{opacity:0;transform-origin:0 0;animation:turnin .14s cubic-bezier(.2,.9,.3,1.3) {T_TURN + 0.06:.2f}s forwards}}
.fhop{{transform-origin:0 0;animation:hop .62s linear {T_FRONT + 0.02:.2f}s both}}
@keyframes turnin{{from{{opacity:1;transform:scale(.08,1.04)}}to{{opacity:1;transform:none}}}}
@keyframes hop{{
0%{{transform:none}}
14%{{transform:scale(1.07,.9)}}
24%{{transform:translateY(-60px) scale(.94,1.09)}}
48%{{transform:translateY(-230px) scale(.98,1.03)}}
70%{{transform:translateY(-20px) scale(.96,1.06)}}
76%{{transform:scale(1.1,.87)}}
88%{{transform:scale(.98,1.03)}}
100%{{transform:none}}}}
.front [data-part=head]{{transform-origin:498px 549px;animation:headlag .62s ease-in-out {T_FRONT + 0.02:.2f}s both}}
@keyframes headlag{{0%,100%{{transform:none}}20%{{transform:translateY(18px)}}45%{{transform:translateY(-14px) rotate(-3deg)}}78%{{transform:translateY(22px) rotate(2deg)}}}}
.front .doodle-blink{{transform-box:fill-box;transform-origin:center;animation:blink .16s ease-in-out {T_FRONT + 0.48:.2f}s both}}
@keyframes blink{{50%{{transform:scaleY(.1)}}}}
.fshadow{{transform-origin:0 0;animation:fshadow .62s linear {T_FRONT + 0.02:.2f}s both;opacity:0}}
@keyframes fshadow{{0%,100%{{opacity:1;transform:none}}48%{{opacity:.5;transform:scale(.6,.6)}}}}
.dust circle,.puff circle{{transform-box:fill-box;transform-origin:center;opacity:0;animation:dust .62s ease-out both}}
@keyframes dust{{0%{{opacity:.55;transform:scale(.3)}}100%{{opacity:0;transform:translate(var(--dx),var(--dy,-60px)) scale(1.35)}}}}
.sweat{{opacity:0;animation:sweat .5s linear both}}
@keyframes sweat{{0%{{opacity:1;transform:translate(0,0) rotate(-20deg)}}100%{{opacity:0;transform:translate(150px,90px) rotate(40deg)}}}}
.speed path{{opacity:0;animation:speed .18s ease-out {T_TURN:.2f}s both}}
@keyframes speed{{0%{{opacity:0}}30%{{opacity:.8}}100%{{opacity:0;transform:translateX(40px)}}}}
@media (prefers-reduced-motion:reduce){{*{{animation-duration:1ms!important;animation-delay:0s!important}}}}
''')
CSS = ''.join(css)


# ======================= particles =======================
def dust(colour):
    out = ''
    for side in ('f', 'b'):  # a puff each time a foot pushes off
        for td, lo, x in plants[side]:
            if T0 < lo < T_STOP:
                tx = x + TOE[0]
                for dx, r, dt in ((40, 30, 0), (90, 20, .05), (-20, 16, .08)):
                    out += f'<circle cx="{tx + dx:.0f}" cy="{-r:.0f}" r="{r}" style="--dx:{dx * 1.4:.0f}px;animation-delay:{lo + dt:.2f}s"/>'
    for i, d in enumerate(STEPS):  # the logo scraping on each surge (at its back corner, his frame)
        t = STEP_T[i] + 0.4 * d
        x = logo_x(t) - 30
        for dx, r, dt in ((30, 26, 0), (95, 16, .05)):
            out += f'<circle cx="{x + dx:.0f}" cy="{-r:.0f}" r="{r}" style="--dx:{dx * 1.5:.0f}px;animation-delay:{t + dt:.2f}s"/>'
    return f'<g class="dust" fill="{colour}">{out}</g>'


def real_dust(colour):
    """Puffs in the real frame: the logo's thud (both ends of its base) and the landing after the hop."""
    out = ''
    for dx, r, dt, dy in ((-120, 40, 0, -90), (-40, 30, .03, -120), (60, 34, .02, -100), (160, 26, .05, -70), (240, 20, .07, -50)):
        x = REAL_END + (0.2 if dx < 0 else 1.7) * u
        out += f'<circle cx="{x:.0f}" cy="{-r:.0f}" r="{r}" style="--dx:{dx * 1.6:.0f}px;--dy:{dy}px;animation-delay:{T_STOP + dt:.2f}s;animation-duration:.8s"/>'
    for dx, r, dt in ((-160, 30, 0), (160, 30, 0), (-80, 22, .04), (90, 22, .04)):
        out += f'<circle cx="{-X_END + dx * 0.4:.0f}" cy="{-r:.0f}" r="{r}" style="--dx:{dx:.0f}px;--dy:-30px;animation-delay:{T_FRONT + 0.46 + dt:.2f}s"/>'
    return f'<g class="dust" fill="{colour}">{out}</g>'


def sweat_drop():
    """One bead of sweat flies off his forehead mid-push (spawned where the head is at that moment)."""
    t = STEP_T[3] + 0.3 * STEPS[3]
    fr = frames[int(t * FPS)]
    head_pt = add(fr['root'], rot(add(R['neck'], (60, -300)), math.radians(fr['torso'][0])))
    drop = f'<path d="M0 -26C10 -10 16 0 16 8A16 16 0 0 1 -16 8C-16 0 -10 -10 0 -26Z" fill="#cfe6f2" stroke="{INK}" stroke-width="6"/>'
    return f'<g transform="translate({head_pt[0]:.0f} {head_pt[1]:.0f})"><g class="sweat" style="animation-delay:{t:.2f}s">{drop}</g></g>'


def exhale(colour):
    fr = frames[int((T_RECOVER + 0.02) * FPS)]
    mouth = add(fr['root'], rot(add(R['neck'], (-140, -60)), math.radians(fr['torso'][0])))
    out = ''.join(f'<circle cx="{mouth[0] + dx:.0f}" cy="{mouth[1] + dy:.0f}" r="{r}" style="--dx:{-60 - dx:.0f}px;--dy:-20px;animation-delay:{T_RECOVER + dt:.2f}s;animation-duration:.5s"/>'
                  for dx, dy, r, dt in ((0, 0, 18, 0), (-30, -10, 14, .04), (-55, 6, 10, .07)))
    return f'<g class="puff" fill="{colour}">{out}</g>'


def speed_lines():
    cy = -HIP_H - 300
    return '<g class="speed" stroke="%s" stroke-width="10" stroke-linecap="round">%s</g>' % (
        INK, ''.join(f'<path d="M{X_END + dx:.0f} {cy + dy:.0f}h{l}"/>' for dx, dy, l in ((-420, -200, 160), (-470, 40, 220), (-430, 280, 140), (300, -120, 160), (340, 160, 200))))


def logo_paths(ink, accent):
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


# The front view: the standing doodle (public/doodle.svg), its feet on the ground where he turned.
front_inner = re.sub(r'^<svg[^>]*>|</svg>$', '', front_svg.strip())
front_inner = re.sub(r'<style>.*?</style>|<!--.*?-->', '', front_inner)
FRONT_FEET = (492, 2140)  # in doodle.svg units: centre between the feet, on the ground


def scene(view, ink, shadow_fill, shadow_op, dust_fill):
    sh = f'fill="{shadow_fill}" opacity="{shadow_op}"'
    torso = (f'<g class="ktorso" style="transform-origin:0 0">{arm("far")}{parts["torso"]}{arm("near")}'
             f'<g transform="translate({R["neck"][0]:.0f} {R["neck"][1]:.0f})"><g class="khead">{parts["head"]}</g></g></g>')
    side = (f'<g class="side"><g class="kshadow"><ellipse cx="0" cy="8" rx="560" ry="40" {sh}/></g>'
            f'<g class="kroot">{leg("b", "line")}{leg("b", "fill")}{leg("f", "line")}{leg("f", "fill")}{torso}</g></g>')
    front = (f'<g transform="translate({-X_END:.0f} 0)"><g class="fshadow"><ellipse cx="0" cy="8" rx="520" ry="40" {sh}/></g>'
             f'<g class="front"><g class="fhop"><g transform="scale({FRONT_SCALE:.4f}) translate({-FRONT_FEET[0]} {-FRONT_FEET[1]})">'
             f'{front_inner.replace("doodle-shadow", "doodle-shadow-x")}</g></g></g></g>')
    logo = (f'<g class="klogo"><ellipse cx="{LOGO_W_SCENE / F / 2:.0f}" cy="8" rx="{LOGO_W_SCENE / F * 0.52:.0f}" ry="40" {sh}/>'
            f'<g class="klogo-b">{logo_paths(ink, "#ff4c24")}</g></g>')
    mirrored = f'<g transform="scale(-1 1)">{dust(dust_fill)}{side}{sweat_drop()}{exhale(dust_fill)}{speed_lines()}</g>'
    world = f'<g transform="translate(0 {GROUND}) scale({F:.5f})">{real_dust(dust_fill)}{logo}{mirrored}{front}</g>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view}" preserveAspectRatio="xMidYMid meet">'
            f'<!-- Generated by scripts/doodle-trace/film.py --><style>{CSS}.doodle-shadow-x{{display:none}}</style>{world}</svg>')


themes = {'light': ('#111111', '#1e2a3a', 0.13, '#9aa3a6'), 'dark': ('#ebe9e4', '#000000', 0.5, '#5b6266')}
views = {'wide': '0 0 1600 1000', 'tall': '130 200 1340 1000'}
for vname, view in views.items():
    for tname, (ink, sf, so, df) in themes.items():
        path = os.path.join(out_dir, f'{vname}-{tname}.svg')
        open(path, 'w').write(scene(view, ink, sf, so, df))
        print(path, os.path.getsize(path))
print(f'{len(frames)} frames, {DURATION:.2f}s; push ends {T_PUSH_END:.2f}, shove {T_SHOVE:.2f}, stop {T_STOP:.2f}, turn {T_TURN:.2f}')
