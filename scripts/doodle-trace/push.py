# Turns the "pushing" pose (push-reference.png) into a vector puppet (rig) for the preloader.
#
# Same tracing method as the standing doodle (matte -> flat colours -> outline silhouette + one smooth
# shape per colour), but the figure is cut into parts that can move freely:
#   thigh-back / thigh-front: pivot at the hip, each holding a shin that pivots at the knee
#   upper: the torso, holding the arms (pivot at the shoulder) and the head (pivot at the neck)
# Joints are round: the shin is cut along a circle round the knee and a matching disc sits under it,
# so a bent knee never opens a gap. The torso is filled in behind the arms, so moving the arms shows
# jacket, not a hole.
#
# Writes rig.svg (a <g> fragment) and rig.json (pivots and sizes) into the current directory;
# scene.py builds the preloader from them.
#   python3 <repo>/scripts/doodle-trace/push.py
import json, os, re
import numpy as np
import vtracer
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
S = 3  # output units per original pixel

# Part boundaries, in original-image pixels.
HEAD = [(466, 320), (592, 320), (592, 396), (574, 416), (568, 436), (548, 458), (526, 476), (500, 472), (480, 462), (468, 444)]
FRONT_ARM = [(368, 458), (432, 456), (442, 503), (512, 508), (586, 512), (594, 526), (588, 562), (470, 562), (420, 554), (368, 548)]
BACK_ARM = [(420, 402), (472, 402), (476, 450), (502, 462), (530, 476), (544, 500), (516, 510), (470, 502), (440, 484), (420, 472)]
TORSO_HULL = [(500, 455), (560, 438), (604, 430), (630, 470), (648, 560), (648, 630), (515, 630), (505, 560), (500, 500)]
FRONT_HIP, BACK_HIP = (538, 615), (596, 618)
FRONT_KNEE, BACK_KNEE = (493, 662), (640, 684)
KNEE_R = 17
SPLIT = [(571, 560), (571, 642), (610, 760), (640, 900)]  # runs down the gap between the legs
SHOULDER, NECK, HIPS = (556, 498), (528, 468), (566, 616)

# ---------- 1. matte: flood the light background in from the edges ----------
src = np.array(Image.open(os.path.join(HERE, 'push-reference.png')).convert('RGB')).astype(int)
H0, W0, _ = src.shape
mn, G, B = src.min(2), src[:, :, 1], src[:, :, 2]


def flood(seed, allow):
    m = seed & allow
    while True:
        n = m.copy()
        n[1:] |= m[:-1]; n[:-1] |= m[1:]; n[:, 1:] |= m[:, :-1]; n[:, :-1] |= m[:, 1:]
        n &= allow
        if (n == m).all():
            return m
        m = n


seed = np.zeros((H0, W0), bool)
seed[0] = seed[-1] = True
seed[:, 0] = seed[:, -1] = True
bg = flood(seed, (mn > 175) & (B <= 251) & (G <= 251))
near = np.zeros_like(bg)
for dy, dx in [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)]:
    near |= np.roll(np.roll(bg, dy, 0), dx, 1)
img = src.astype(float)
img[near & ~bg] = (30, 44, 56)
img[bg] = (30, 44, 56)
ys, xs = np.where(~bg)
x0, x1, y0, y1 = xs.min() - 30, xs.max() + 30, ys.min() - 30, ys.max() + 30
crop = Image.fromarray(img.clip(0, 255).astype(np.uint8)).crop((x0, y0, x1, y1))
W, H = crop.width * S, crop.height * S
rgb = crop.resize((W, H), Image.LANCZOS)
alpha = np.array(Image.fromarray((~bg * 255).astype(np.uint8)).crop((x0, y0, x1, y1)).resize((W, H), Image.BILINEAR)) > 127

# ---------- 2. flatten colours (k-means over the figure) and name them ----------
K = 12
A = np.array(rgb).reshape(-1, 3).astype(float)
X = A[alpha.reshape(-1)]
rng = np.random.default_rng(1)
smp = X[rng.choice(len(X), min(60000, len(X)), replace=False)]
cent = [smp[0]]
for _ in range(K - 1):
    cent.append(smp[np.argmax(np.min([((smp - c) ** 2).sum(1) for c in cent], 0))])
cent = np.array(cent)
for _ in range(30):
    lab = np.argmin(((smp[:, None, :] - cent[None]) ** 2).sum(2), 1)
    cent = np.array([smp[lab == k].mean(0) if (lab == k).any() else cent[k] for k in range(K)])
lab = np.zeros(len(A), int)
for s0 in range(0, len(A), 200000):
    lab[s0:s0 + 200000] = np.argmin(((A[s0:s0 + 200000, None, :] - cent[None]) ** 2).sum(2), 1)
lab = np.array(Image.fromarray(lab.reshape(H, W).astype(np.uint8), 'L').filter(ImageFilter.ModeFilter(5)))
P = {'ink': [(12, 24, 30), (34, 53, 61)], 'hair': [(56, 74, 81)], 'slate': [(97, 107, 114)],
     'green': [(67, 106, 95)], 'white': [(250, 253, 252), (232, 240, 243)], 'shade': [(205, 218, 222)],
     'lime': [(151, 183, 165)], 'noise': [(133, 163, 148), (111, 133, 129), (181, 195, 198)]}
refs = [(k, np.array(c)) for k, cs in P.items() for c in cs]
cls = np.full((H, W), '', object)
for k in range(K):
    cls[(lab == k) & alpha] = min(refs, key=lambda r: ((r[1] - cent[k]) ** 2).sum())[0]


def boxsum(m, r):
    c = np.pad(m.astype(np.int32), ((r + 1, r), (r + 1, r))).cumsum(0).cumsum(1)
    return c[2 * r + 1:, 2 * r + 1:] - c[:-2 * r - 1, 2 * r + 1:] - c[2 * r + 1:, :-2 * r - 1] + c[:-2 * r - 1, :-2 * r - 1]


names = [k for k in P if k != 'noise']
best = np.array(names, object)[np.stack([boxsum(cls == k, 4) for k in names]).argmax(0)]
cls[cls == 'noise'] = best[cls == 'noise']
FILL = {k: '#%02x%02x%02x' % tuple(int(v) for v in A[((cls == k) & alpha).reshape(-1)].mean(0))
        for k in names if ((cls == k) & alpha).any()}
FILL['ink'] = '#1b2d39'
ORDER = ['hair', 'slate', 'green', 'white', 'lime', 'shade']

# ---------- 3. geometry helpers (original-pixel coordinates) ----------
yy, xx = np.mgrid[0:H, 0:W]
ox, oy = xx / S + x0, yy / S + y0
U = lambda p: ((p[0] - x0) * S, (p[1] - y0) * S)


def poly(pts):
    inside = np.zeros((H, W), bool)
    for i in range(len(pts)):
        (xa, ya), (xb, yb) = pts[i], pts[(i + 1) % len(pts)]
        inside ^= ((ya > oy) != (yb > oy)) & (ox < (xb - xa) * (oy - ya) / (yb - ya + 1e-9) + xa)
    return inside


def dil(m, r):
    o = m.copy()
    for _ in range(r):
        n = o.copy(); n[1:] |= o[:-1]; n[:-1] |= o[1:]; n[:, 1:] |= o[:, :-1]; n[:, :-1] |= o[:, 1:]; o = n
    return o


def smooth(mask):
    return np.array(Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3.6))) > 127


def layers_for(c):
    """Smoothed outline silhouette + colour layers for a class map (each colour tucks under later ones)."""
    out = {'ink': smooth(c != '')}
    for i, k in enumerate(ORDER):
        m = c == k
        m = m | (dil(m, 2) & np.isin(c, ORDER[i + 1:]))
        out[k] = smooth(m) & out['ink']
    return out


# ---------- 4. parts ----------
head = poly(HEAD) & alpha
arms = (poly(FRONT_ARM) | poly(BACK_ARM)) & alpha & ~head
jacket = np.isin(cls, ['green', 'lime', 'white'])
legs = (oy >= 600) & ~dil(jacket, 3 * S) & alpha
back_side = poly(SPLIT + [(800, 900), (800, 560)])
leg_back, leg_front = legs & back_side, legs & ~back_side
torso = alpha & ~legs & ~head & ~arms

# Fill the torso in behind the arms: each column takes the colour found a little below the hole
# (so the tee strip and the jacket's front edges simply continue upwards).
hole = poly(TORSO_HULL) & arms
tcls = np.where(torso, cls, '').astype(object)
for x in np.where(hole.any(0))[0]:
    col = np.where(hole[:, x])[0]
    probe = [y for y in range(col.max() + 4 * S, min(H, col.max() + 12 * S)) if torso[y, x]]
    probe = probe or [y for y in range(col.min() - 4 * S, max(0, col.min() - 12 * S), -1) if torso[y, x]]
    tcls[col, x] = tcls[probe[0], x] if probe else 'green'
torso_full = torso | hole

full = layers_for(np.where(alpha, cls, '').astype(object))
torso_layers = layers_for(tcls)


def split_knee(leg, hip, knee):
    """Thigh keeps everything up to the knee plus the knee disc; the shin is the rest, minus the disc."""
    kx, ky = knee
    dx, dy = kx - hip[0], ky - hip[1]
    past = (ox - kx) * dx + (oy - ky) * dy > 0
    disc = (ox - kx) ** 2 + (oy - ky) ** 2 <= KNEE_R ** 2
    return (leg & ~past) | (leg & disc), leg & past & ~disc


thigh_f, shin_f = split_knee(leg_front, FRONT_HIP, FRONT_KNEE)
thigh_b, shin_b = split_knee(leg_back, BACK_HIP, BACK_KNEE)

# ---------- 5. trace ----------
n_trace = [0]


def trace(mask, speckle=60):
    n_trace[0] += 1
    f = f'_t{n_trace[0]}'
    Image.fromarray(np.where(mask, 0, 255).astype(np.uint8)).save(f + '.png')
    vtracer.convert_image_to_svg_py(f + '.png', f + '.svg', colormode='binary', mode='spline', filter_speckle=speckle,
                                    corner_threshold=60, length_threshold=4.0, splice_threshold=45, path_precision=0)
    s = open(f + '.svg').read()
    os.remove(f + '.png'); os.remove(f + '.svg')
    return ''.join(f'<path transform="translate({round(float(tx))} {round(float(ty))})" d="{d.strip()}"/>'
                   for d, tx, ty in re.findall(r'<path d="([^"]*)" fill="[^"]*" transform="translate\(([-\d.]+),([-\d.]+)\)"', s))


def shapes(lay, cut, spill=None, speckle=60, only=None):
    """Outline + colour shapes for one part. Colours may spill a little past a cut edge (over the
    part's own outline there), so a cut never shows as a thin dark line."""
    out = ''
    for k in ['ink'] + (only or ORDER):
        m = lay[k] & (cut if k == 'ink' or spill is None else spill)
        if m.sum() and k in FILL:
            out += f'<g fill="{FILL[k]}">' + trace(m, speckle) + '</g>'
    return out


def g(name, pivot, inner):
    px, py = U(pivot)
    o = f'style="transform-origin:{px:.0f}px {py:.0f}px"'
    # two nested groups per joint, so a looping cycle and a one-off move can animate together
    return f'<g class="r-{name}" {o}><g class="r-{name}-b" {o}>{inner}</g></g>'


def knee_disc(knee):
    kx, ky = U(knee)
    return (f'<circle cx="{kx:.0f}" cy="{ky:.0f}" r="{KNEE_R * S - 2}" fill="{FILL["slate"]}" '
            f'stroke="{FILL["ink"]}" stroke-width="{3.2 * S:.0f}"/>')


grow = lambda m, r: dil(m, r) & alpha
LEG_COLOURS = ['slate']  # pants and shoes: only the grey (stray light specks at the edges are dropped)
leg_svg = {}
for name, thigh, shin, hip, knee, other in [('back', thigh_b, shin_b, BACK_HIP, BACK_KNEE, leg_front),
                                            ('front', thigh_f, shin_f, FRONT_HIP, FRONT_KNEE, None)]:
    # A thigh reaches up under the jacket, and the back thigh also tucks under the front leg,
    # but neither ever overlaps its own shin (that would show when the knee bends).
    t = thigh | (grow(thigh, 6) & ~legs)
    if other is not None:
        t |= dil(thigh, 40) & other
    shin_svg = g(f'shin-{name}', knee, shapes(full, shin, spill=grow(shin, 2) & ~thigh, only=LEG_COLOURS))
    leg_svg[name] = g(f'thigh-{name}', hip, knee_disc(knee) + shin_svg + shapes(full, t, spill=grow(t, 4) & ~legs | t, only=LEG_COLOURS))

torso_svg = shapes(torso_layers, grow(torso_full, 6))
torso_svg += f'<g fill="{FILL["ink"]}">' + trace(full['ink'] & head & (oy >= 430)) + '</g>'  # dark backing behind the chin
arms_svg = g('arms', SHOULDER, shapes(full, arms, spill=grow(arms, 5) & ~head))
head_svg = g('head', NECK, shapes(full, head, spill=grow(head, 4), speckle=10))  # fine detail: glasses, eyes
rig = g('body', HIPS, leg_svg['back'] + leg_svg['front'] + g('upper', HIPS, torso_svg + arms_svg + head_svg))
open('rig.svg', 'w').write(rig)
meta = {'w': W, 'h': H, 'ground': U((0, 783))[1], 'front_hand': U((372, 500)), 'back_hand': U((425, 440)),
        'front_foot': U((490, 760)), 'back_foot': U((700, 775)), 'fills': FILL}
json.dump(meta, open('rig.json', 'w'), default=float)
print('rig bytes', len(rig), {k: v for k, v in meta.items() if k != 'fills'})
