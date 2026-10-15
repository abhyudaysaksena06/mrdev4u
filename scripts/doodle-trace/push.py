# Traces the upper body of the "pushing" drawing (push-reference.png) for the preloader film.
#
# Same tracing method as the standing doodle (matte -> flat colours -> outline silhouette + one smooth
# shape per colour), cut into the parts the film moves: the torso (filled in behind the arms), the
# head and the two hands. Sleeves and legs are not traced: film.py draws new ones that can bend.
#
# Writes parts.json (torso, head and the two hands as <g> fragments, each with its pivot at the
# origin) and rig.json (pivots, colours) into the current directory; film.py builds the film.
#   python3 <repo>/scripts/doodle-trace/push.py
import json, math, os, re
import numpy as np
import vtracer
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
S = 3  # output units per original pixel

# Part boundaries, in original-image pixels.
HEAD = [(462, 320), (592, 320), (592, 396), (574, 416), (568, 436), (548, 458), (526, 476), (500, 472), (480, 462), (474, 452), (474, 410), (462, 408)]
FRONT_ARM = [(368, 458), (432, 456), (442, 503), (512, 508), (586, 512), (594, 526), (588, 562), (470, 562), (420, 554), (368, 548)]
BACK_ARM = [(420, 402), (472, 402), (476, 450), (502, 462), (530, 476), (544, 500), (516, 510), (470, 502), (440, 484), (420, 472)]
TORSO_HULL = [(500, 455), (560, 438), (604, 430), (630, 470), (648, 560), (648, 630), (515, 630), (505, 560), (500, 500)]
FRONT_HIP, BACK_HIP = (538, 615), (596, 618)
NECK, HIPS = (528, 468), (566, 616)
# The film draws new sleeves; only the hands are kept, cut at the wrist (the cuff covers the cut).
NEAR_HAND = [(370, 460), (428, 460), (428, 510), (416, 514), (416, 545), (370, 548)]
FAR_HAND = [(418, 405), (462, 405), (462, 409), (474, 412), (474, 452), (460, 456), (456, 466), (452, 484), (418, 484)]
NEAR_WRIST, FAR_WRIST = (419, 528), (465, 467)
NEAR_SHOULDER, FAR_SHOULDER = (585, 507), (560, 478)
NEAR_PALM, FAR_PALM = (385, 507), (430, 447)  # where each palm meets the surface it pushes

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
torso = alpha & ~legs & ~head & ~arms
torso &= ~((oy >= 600) & ~dil(jacket, 1 * S))  # nothing of the old legs below the hem (walk.py draws new ones)

# Fill the torso in behind the arms: jacket green, with the tee strip continuing as one slanted band
# from the collar to the hem (it runs that way in the drawing), outlined like the visible parts.
hole = poly(TORSO_HULL) & arms
tcls = np.where(torso, cls, '').astype(object)
TEE_L, TEE_R = ((512, 470), (541, 610)), ((531, 470), (574, 610))  # the strip's two edges


def side_of(line):
    (xa, ya), (xb, yb) = line
    return (ox - xa) * (yb - ya) - (oy - ya) * (xb - xa)  # >0 right of the line (looking down it)


def dist_to(line):
    (xa, ya), (xb, yb) = line
    return np.abs(side_of(line)) / math.hypot(xb - xa, yb - ya)


inside_tee = (side_of(TEE_L) > 0) & (side_of(TEE_R) < 0)
tcls[hole] = 'green'
tcls[hole & inside_tee] = 'white'
tcls[hole & ((dist_to(TEE_L) < 1.8) | (dist_to(TEE_R) < 1.8))] = 'ink'
torso_full = torso | hole
# the filled-in chest needs an outline where it meets the outside (it used to be hidden by the arms)
outside = ~poly(TORSO_HULL)
edge = hole & dil(outside, int(3.4 * S))
tcls[edge] = 'ink'

full = layers_for(np.where(alpha, cls, '').astype(object))
torso_layers = layers_for(tcls)


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


grow = lambda m, r: dil(m, r) & alpha

torso_svg = shapes(torso_layers, grow(torso_full, 6))
torso_svg += f'<g fill="{FILL["ink"]}">' + trace(full['ink'] & head & (oy >= 430)) + '</g>'  # dark backing behind the chin
head_svg = shapes(full, head, spill=grow(head, 4), speckle=10)  # fine detail: glasses, eyes
hx, hy = U(HIPS)
rel = lambda p: (U(p)[0] - hx, U(p)[1] - hy)


def piece(svg, origin):
    """Wrap traced shapes so that `origin` (original pixels) sits at 0,0."""
    ox_, oy_ = U(origin)
    return f'<g transform="translate({-ox_:.0f} {-oy_:.0f})">{svg}</g>'


hand_near = poly(NEAR_HAND) & alpha
hand_far = poly(FAR_HAND) & alpha
parts = {
    'torso': piece(torso_svg, HIPS),
    'head': piece(head_svg, NECK),
    'hand_near': piece(shapes(full, hand_near, spill=grow(hand_near, 3) & poly(NEAR_HAND), speckle=10), NEAR_WRIST),
    'hand_far': piece(shapes(full, hand_far, spill=grow(hand_far, 3) & poly(FAR_HAND), speckle=10), FAR_WRIST),
}
json.dump(parts, open('parts.json', 'w'))
meta = {'fills': FILL, 'scale': S, 'ground': U((0, 783))[1] - hy,
        'rel': {k: rel(v) for k, v in {'front_hip': FRONT_HIP, 'back_hip': BACK_HIP, 'neck': NECK,
                                        'near_shoulder': NEAR_SHOULDER, 'far_shoulder': FAR_SHOULDER,
                                        'near_wrist': NEAR_WRIST, 'far_wrist': FAR_WRIST}.items()},
        # palm contact points relative to their wrist
        'palm': {'near': (U(NEAR_PALM)[0] - U(NEAR_WRIST)[0], U(NEAR_PALM)[1] - U(NEAR_WRIST)[1]),
                 'far': (U(FAR_PALM)[0] - U(FAR_WRIST)[0], U(FAR_PALM)[1] - U(FAR_WRIST)[1])}}
json.dump(meta, open('rig.json', 'w'), default=float)
print('parts:', {k: len(v) for k, v in parts.items()}, meta['rel'], meta['palm'])
