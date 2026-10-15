# Reads the reference drawing so the 3D model can take its details from it directly:
# the hair's exact outline, and every ink line the model's own outlines do not already draw.
import os
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import measure

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, '..', 'doodle-trace', 'reference.png')


def rgb(path=REF):
    return np.array(Image.open(path).convert('RGB')).astype(int)


def near(a, hexc, tol):
    c = np.array([int(hexc[i:i + 2], 16) for i in (1, 3, 5)])
    return np.sqrt(((a - c) ** 2).sum(-1)) < tol


def ink(a):
    """Ink lines: dark pixels (after a median filter against the drawing's speckle), minus thick dark
    fills such as the navy hood lining, which is about as dark but far wider than any line."""
    m = np.stack([ndi.median_filter(a[..., c].astype(float), 3) for c in range(3)], -1)
    dark = (0.3 * m[..., 0] + 0.59 * m[..., 1] + 0.11 * m[..., 2]) < 64
    dt = ndi.distance_transform_edt(dark)
    core = dt > 6.5
    fill = ndi.binary_dilation(core, disk(7)) & dark
    return dark & ~fill


def disk(r):
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r


def hair_mask():
    """The hair's slate fill (strand lines filled in), above the ears."""
    a = rgb()
    m = near(a, '#3f4d5a', 26)
    m[265:] = False
    m[:, :296] = False
    m[:, 476:] = False
    m = ndi.binary_closing(m, disk(5))   # fill the ink strand lines and speckle inside the hair
    m = ndi.binary_fill_holes(m)
    skin = (a.min(-1) > 200)             # ...but never over the face showing between the locks
    m &= ~ndi.binary_dilation(skin, disk(1))
    brows = ink(a)
    brows[:238] = False                  # brows sit under the fringe: not hair
    m &= ~brows
    m = ndi.binary_opening(m, disk(2))   # and drop hairline-thin bits along the edge
    lab, n = ndi.label(m)
    sizes = ndi.sum(m, lab, range(1, n + 1))
    keep = [i + 1 for i, s in enumerate(sizes) if s > 400]
    return np.isin(lab, keep)


def missing_lines(model_png, tol=4, min_area=14, head_y=345, body_gap=6):
    """Ink in the drawing that the model's render does not have (within tol px).

    On the head every such line is kept (face features, hair strands). On the body, lines that
    only shadow one of the model's outlines a few px away (a silhouette slightly off) are dropped;
    lines well inside a part (folds, seams) are kept."""
    want = ink(rgb())
    im = Image.open(model_png).convert('RGBA')
    bg = Image.new('RGBA', im.size, (230, 236, 236, 255))
    bg.alpha_composite(im)
    have = ink(np.array(bg.convert('RGB')).astype(int))
    miss = want & ~ndi.binary_dilation(have, disk(tol))
    miss = ndi.binary_opening(miss, disk(1))  # drop slivers along outlines that only differ in width
    far = ndi.distance_transform_edt(~have)
    lab, n = ndi.label(miss)
    keep = np.zeros(n + 1, bool)
    for i, sl in enumerate(ndi.find_objects(lab)):
        reg = lab[sl] == i + 1
        if reg.sum() < min_area:
            continue
        cy = sl[0].start + np.nonzero(reg)[0].mean()
        keep[i + 1] = cy < head_y or np.median(far[sl][reg]) > body_gap
    return keep[lab]


def regions(mask, up=4, blur=0.9):
    """Smooth outline polygons (px, x/y) of each connected region: [(outer, [holes])]."""
    out = []
    lab, n = ndi.label(mask)
    for i, sl in enumerate(ndi.find_objects(lab)):
        sub = lab[sl] == i + 1
        sub = np.pad(sub, 2)
        big = ndi.zoom(sub.astype(float), up, order=1)
        big = ndi.gaussian_filter(big, blur * up)
        cs = measure.find_contours(big, 0.5)
        y0, x0 = sl[0].start - 2, sl[1].start - 2
        loops = []
        for c in cs:
            if len(c) < 8:
                continue
            pts = [(x0 + (p[1] + 0.5) / up - 0.5, y0 + (p[0] + 0.5) / up - 0.5) for p in c[::2]]
            area = 0.5 * sum(pts[k][0] * pts[k - 1][1] - pts[k - 1][0] * pts[k][1] for k in range(len(pts)))
            loops.append((abs(area), pts))
        if not loops:
            continue
        loops.sort(key=lambda l: -l[0])
        out.append(([p for _, p in loops][0], [p for _, p in loops][1:]))
    return out


def colour_class(a):
    """Per pixel: 'lime', 'navy' or 'green' (anything else in the hood falls back to green)."""
    m = np.stack([ndi.median_filter(a[..., c].astype(float), 3) for c in range(3)], -1)
    lime = near(m, '#9fcc99', 45)
    navy = np.sqrt(((m - np.array([30, 57, 76])) ** 2).sum(-1)) < 22
    # clean edges: a majority vote over a small disc
    k = disk(2).astype(float)
    k /= k.sum()
    lime = ndi.convolve(lime.astype(float), k) > 0.5
    navy = ndi.convolve(navy.astype(float), k) > 0.5
    out = np.full(a.shape[:2], 'green', object)
    out[lime] = 'lime'
    out[navy] = 'navy'
    return out


def hood_mask():
    """The hood's rim and lining on both sides of the neck: the region the drawing encloses with
    ink between the shoulders and the neck, found by flooding from inside the rim."""
    a = rgb()
    wall = ndi.binary_dilation(ink(a), disk(1))
    light = ndi.median_filter(a.min(-1), 3) > 170   # skin, tee (the lime piping is not this light)
    free = ~wall & ~ndi.binary_dilation(light, disk(1))
    free[:312] = False
    free[412:] = False
    lab, n = ndi.label(free)
    keep = {lab[y, x] for x, y in ((329, 340), (444, 340), (343, 350), (428, 350))} - {0}
    m = np.isin(lab, list(keep))
    m = ndi.binary_dilation(m, disk(1)) & ~ink(a)  # back up to the ink line's centre
    return ndi.binary_fill_holes(m)
