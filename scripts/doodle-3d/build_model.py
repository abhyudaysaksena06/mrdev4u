# Builds the doodle character (scripts/doodle-trace/reference.png) as a rigged 3D toon model.
#
#   pip install bpy==5.2.2          # Blender as a Python module, runs headless
#   python3 build_model.py <out_dir> [--render] [--glb]
#
# Writes <out_dir>/doodle.blend, plus front/three-quarter/side/back renders with --render and
# <out_dir>/doodle.glb (skinned, for three.js) with --glb. The committed doodle.blend next to this
# script is its output; preview/ has the turnaround and a rig test.
#
# Rig (60 bones, at the anatomical joint centres): root > hips > spine > chest > neck > head;
# per side shoulder > upper_arm > forearm (+ forearm_twist) > hand > three bones per finger and
# thumb; thigh > shin > foot. Joints have human ranges (elbows and knees hinge one way only, finger
# joints curl, the wrist's turn is shared with the forearm so it never wrings). Legs are IK
# (foot_ik, knee_pole; planted feet stay flat); arms are FK with an IK (hand_ik, elbow_pole) to
# switch on for pushes and grabs. posing.py has helpers to pose and render it.
#
# Everything is measured in pixels of the reference drawing (x right, y down, d = depth, negative
# toward the viewer) and converted to metres by P(): the figure stands 1.75 m tall on the origin,
# facing -Y, the Blender convention (so the character's left, ".L", is +X).
#
# The look matches the drawing: flat unlit colours and an ink outline. The outline is an "inverted
# hull" (a slightly larger copy of each mesh, faces flipped, drawn in ink only where it shows behind
# the surface), so it is real geometry that deforms with the rig and exports to three.js.
import bpy, bmesh, math, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trace as tr
from scipy import ndimage as ndi
from math import sin, cos, pi, radians, asin, atan2, sqrt
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

args = [a for a in sys.argv[1:] if not a.startswith('--')]
OUT = os.path.abspath(args[0] if args else '.')
os.makedirs(OUT, exist_ok=True)

CX, FLOOR = 386, 866          # centre line and floor of the reference drawing, px
S = 1.75 / (FLOOR - 160)      # metres per px (hair top is at y=160)
LINE = 5.0                    # outline width in the drawing, px


def P(x, y, d=0.0):
    return Vector(((x - CX) * S, d * S, (FLOOR - y) * S))


def srgb(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c]


PAL = {
    'ink': '#1b2d39', 'hair': '#3f4d5a', 'pants': '#3e4b56', 'shoe': '#3c4955', 'sole': '#2c3a45',
    'hoodie': '#426a5f', 'hoodin': '#2f4f47', 'lime': '#9fcc99', 'skin': '#fafdfc', 'shade': '#c4d5dc',
    'tee': '#fbfdfc', 'navy': '#1e394c', 'string': '#eef4f2', 'shadow': '#c6d4dd',
}

# ---------------------------------------------------------------- scene
bpy.ops.wm.read_factory_settings(use_empty=True)
SC = bpy.context.scene
COL = bpy.data.collections.new('doodle')
SC.collection.children.link(COL)


def flat(name):
    """Unlit flat colour (emission), what the drawing uses."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    e = nt.nodes.new('ShaderNodeEmission')
    e.inputs['Color'].default_value = (*srgb(PAL[name]), 1)
    o = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(e.outputs[0], o.inputs[0])
    m.diffuse_color = (*srgb(PAL[name]), 1)
    return m


def outline_mat():
    """Ink on the far side of the hull only (Cycles ignores backface culling, so do it in the shader)."""
    if 'outline' in bpy.data.materials:
        return bpy.data.materials['outline']
    m = bpy.data.materials.new('outline')
    m.use_nodes = True
    m.use_backface_culling = True
    nt = m.node_tree
    nt.nodes.clear()
    g = nt.nodes.new('ShaderNodeNewGeometry')
    e = nt.nodes.new('ShaderNodeEmission')
    e.inputs['Color'].default_value = (*srgb(PAL['ink']), 1)
    t = nt.nodes.new('ShaderNodeBsdfTransparent')
    mix = nt.nodes.new('ShaderNodeMixShader')
    o = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(g.outputs['Backfacing'], mix.inputs[0])
    nt.links.new(e.outputs[0], mix.inputs[1])
    nt.links.new(t.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], o.inputs[0])
    m.diffuse_color = (*srgb(PAL['ink']), 1)
    return m


# ---------------------------------------------------------------- mesh helpers
def new_obj(name, verts, faces, mats):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    COL.objects.link(ob)
    for m in mats:
        me.materials.append(flat(m))
    for p in me.polygons:
        p.use_smooth = True
    return ob


def ring(c, u, v, rx, ry, n=24, e=2.0, a0=0.0, a1=2 * pi, closed=True):
    """n points on a (super)ellipse around c; angle 0 is +u, 90 degrees is +v."""
    k = n if closed else n - 1
    out = []
    for i in range(n):
        t = a0 + (a1 - a0) * i / k
        cx, sy = cos(t), sin(t)
        px = math.copysign(abs(cx) ** (2 / e), cx)
        py = math.copysign(abs(sy) ** (2 / e), sy)
        out.append(c + u * (rx * px) + v * (ry * py))
    return out


def loft(name, rings, mats, closed=True, caps=(None, None)):
    """Quads between consecutive rings; caps are pole points (or None for an open end)."""
    n = len(rings[0])
    verts = [v for r in rings for v in r]
    faces = []
    m = n if closed else n - 1
    for i in range(len(rings) - 1):
        for j in range(m):
            faces.append((i * n + j, i * n + (j + 1) % n, (i + 1) * n + (j + 1) % n, (i + 1) * n + j))
    for end, pole in enumerate(caps):
        if pole is None:
            continue
        verts.append(pole)
        c = len(verts) - 1
        base = 0 if end == 0 else (len(rings) - 1) * n
        for j in range(m):
            a, b = base + j, base + (j + 1) % n
            faces.append((b, a, c) if end == 0 else (a, b, c))
    ob = new_obj(name, verts, faces, mats)
    fix_normals(ob)
    return ob


def hring(y, hw, hd, dc=0.0, x=CX, n=24, e=2.0, **kw):
    """Horizontal ring at drawing height y (vertical tubes: torso, neck, legs)."""
    return ring(P(x, y, dc), Vector((1, 0, 0)), Vector((0, 1, 0)), hw * S, hd * S, n, e, **kw)


def frames(pts, ref):
    """Centre, tangent and side vectors along a path of px points (x, y, d); ref is the side hint."""
    C = [P(*p) for p in pts]
    out = []
    for i, c in enumerate(C):
        t = (C[min(i + 1, len(C) - 1)] - C[max(i - 1, 0)]).normalized()
        r = ref(i, c) if callable(ref) else ref
        u = (r - t * r.dot(t)).normalized()
        out.append((c, t, u, t.cross(u)))
    return out


def tube(name, pts, radii, mats, ref=Vector((1, 0, 0)), n=24, e=2.0, caps=(0.8, 0.8)):
    """Tube along a path; radii are px (r or (r_side, r_depth)); caps round off the ends."""
    F = frames(pts, ref)
    rings, ends = [], []
    for (c, t, u, v), r in zip(F, radii):
        rx, ry = (r, r) if not isinstance(r, tuple) else r
        rings.append(ring(c, u, v, rx * S, ry * S, n, e))
    for k, (i, sg) in enumerate(((0, -1), (-1, 1))):
        if caps[k] is None:
            ends.append(None)
            continue
        c, t = F[i][0], F[i][1]
        r = radii[i] if not isinstance(radii[i], tuple) else min(radii[i])
        ends.append(c + t * (sg * r * caps[k] * S))
    ob = loft(name, rings, mats, caps=tuple(ends))
    ob['path'] = [list(p) for p in pts]
    return ob


def ellipsoid(name, c, r, mats, rot=(0, 0, 0), n=24):
    """c in px (x, y, d); r = (half width, half height, half depth) px; rot in degrees (x, y, z)."""
    rings = []
    k = n // 2
    for i in range(1, k):
        a = -pi / 2 + pi * i / k
        rings.append(ring(Vector((0, 0, sin(a) * r[1] * S)), Vector((1, 0, 0)), Vector((0, 1, 0)),
                          cos(a) * r[0] * S, cos(a) * r[2] * S, n))
    ob = loft(name, rings, mats, caps=(Vector((0, 0, -r[1] * S)), Vector((0, 0, r[1] * S))))
    ob.rotation_euler = [radians(a) for a in rot]
    ob.location = P(*c)
    apply_transform(ob)
    return ob


def fix_normals(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()


def apply_transform(ob):
    ob.data.transform(ob.matrix_basis)
    ob.matrix_basis = Matrix.Identity(4)


def apply_mods(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    me.name = ob.name
    bpy.data.meshes.remove(old)


def smooth(ob, levels=2):
    m = ob.modifiers.new('subd', 'SUBSURF')
    m.levels = m.render_levels = levels
    apply_mods(ob)


def solidify(ob, px, inner_mat=None):
    if inner_mat:
        ob.data.materials.append(flat(inner_mat))
    m = ob.modifiers.new('solid', 'SOLIDIFY')
    m.thickness = px * S
    m.offset = -1
    m.use_rim = True
    if inner_mat:
        m.material_offset = len(ob.data.materials) - 1
        m.material_offset_rim = 0
    apply_mods(ob)


def paint(ob, fn):
    """Give each face the material fn(face centre in px, face) returns (a name in PAL) or keep it."""
    names = [m.name for m in ob.data.materials]
    for p in ob.data.polygons:
        w = ob.matrix_world @ p.center
        px = (w.x / S + CX, FLOOR - w.z / S, w.y / S)
        k = fn(px, p)
        if k:
            if k not in names:
                ob.data.materials.append(flat(k))
                names.append(k)
            p.material_index = names.index(k)


CLS = None


def paint_drawing(ob, allowed, where=lambda x, y: True, facing=0.5):
    """Faces that look at the viewer take the drawing's own colour at that spot, if it is one of
    `allowed` (e.g. the soft shade under the chin); the rest keep their colour."""
    global CLS
    if CLS is None:
        CLS = tr.colour_class(tr.rgb())

    def fn(p, f):
        if f.normal.y > -facing or not where(p[0], p[1]):
            return None
        c = CLS[int(round(p[1])), int(round(p[0]))]
        return c if c in allowed else None
    paint(ob, fn)


def tube_angle(ob, ref):
    """Angle function for faces of a tube: degrees around the path from its side vector."""
    F = frames([tuple(p) for p in ob['path']], ref)

    def ang(pt):
        w = P(*pt)
        best = None
        for i in range(len(F) - 1):
            a, b = F[i][0], F[i + 1][0]
            ab = b - a
            t = max(0, min(1, (w - a).dot(ab) / ab.length_squared))
            q = a + ab * t
            dd = (w - q).length
            if best is None or dd < best[0]:
                best = (dd, i, t, q)
        _, i, t, q = best
        u = F[i][2].lerp(F[i + 1][2], t).normalized()
        v = F[i][3].lerp(F[i + 1][3], t).normalized()
        r = w - q
        return math.degrees(atan2(r.dot(v), r.dot(u))), i + t
    return ang


def decal(name, polys, target_objs, mat, lift=0.8, closed_fill=True):
    """Flat shapes drawn in drawing px, dropped along the view axis onto the target surfaces."""
    dg = bpy.context.evaluated_depsgraph_get()
    trees = [BVHTree.FromObject(o, dg) for o in target_objs]

    last = [None]

    def drop(x, y):
        o = P(x, y, -400)
        hits = [t.ray_cast(o, Vector((0, 1, 0))) for t in trees]
        hits = [h for h in hits if h[0] is not None]
        if not hits:  # just off the edge: stay at the depth of the last point that landed
            p, nrm = last[0] or (P(x, y, 0), Vector((0, -1, 0)))
            return Vector((P(x, y).x, p.y, P(x, y).z)), nrm
        h = min(hits, key=lambda h: h[3])
        last[0] = (h[0], h[1])
        return h[0], h[1]
    verts, faces = [], []
    for poly in polys:
        base = len(verts)
        if isinstance(poly, dict):  # a stroke: quads between its two edges
            L, R = poly['strip']
            for x, y in L + R:
                p, nrm = drop(x, y)
                verts.append(p + nrm * (lift * S))
            n = len(L)
            for j in range(n - 1):
                faces.append((base + j, base + j + 1, base + n + j + 1, base + n + j))
            continue
        for x, y in poly:
            p, nrm = drop(x, y)
            verts.append(p + nrm * (lift * S))
        if closed_fill:
            cx = sum(p[0] for p in poly) / len(poly)
            cy = sum(p[1] for p in poly) / len(poly)
            p, nrm = drop(cx, cy)
            verts.append(p + nrm * (lift * S))
            c = len(verts) - 1
            for j in range(len(poly)):
                faces.append((base + j, base + (j + 1) % len(poly), c))
    ob = new_obj(name, verts, faces, [mat])
    for p in ob.data.polygons:
        p.use_smooth = False
    fix_facing(ob)
    return ob


def fix_facing(ob):
    """Decals face the viewer (-Y)."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    flip = [f for f in bm.faces if f.normal.y > 0]
    bmesh.ops.reverse_faces(bm, faces=flip)
    bm.to_mesh(ob.data)
    bm.free()


def stroke(pts, w0, w1=None, n=6, cap=True):
    """A thick polyline as a closed outline polygon (px), width tapering from w0 to w1."""
    w1 = w0 if w1 is None else w1
    # resample with Catmull-Rom for smooth curves
    sm = []
    for i in range(len(pts) - 1):
        p0 = Vector(pts[max(i - 1, 0)]); p1 = Vector(pts[i]); p2 = Vector(pts[i + 1]); p3 = Vector(pts[min(i + 2, len(pts) - 1)])
        for k in range(n):
            t = k / n
            sm.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    sm.append(Vector(pts[-1]))
    L, R = [], []
    for i, p in enumerate(sm):
        a = sm[max(i - 1, 0)]; b = sm[min(i + 1, len(sm) - 1)]
        t = (b - a).normalized()
        nrm = Vector((-t.y, t.x))
        f = i / (len(sm) - 1)
        w = (w0 + (w1 - w0) * f) / 2
        L.append(p + nrm * w); R.append(p - nrm * w)
    return {'strip': ([tuple(p) for p in L], [tuple(p) for p in R])}


def oval(cx, cy, rx, ry, n=20, rot=0):
    a = radians(rot)
    return [(cx + rx * cos(t) * cos(a) - ry * sin(t) * sin(a), cy + rx * cos(t) * sin(a) + ry * sin(t) * cos(a))
            for t in (2 * pi * i / n for i in range(n))]


def rrect(cx, cy, w, h, r, n=6):
    pts = []
    for (qx, qy, a0) in ((cx + w / 2 - r, cy - h / 2 + r, -90), (cx + w / 2 - r, cy + h / 2 - r, 0),
                         (cx - w / 2 + r, cy + h / 2 - r, 90), (cx - w / 2 + r, cy - h / 2 + r, 180)):
        for k in range(n + 1):
            t = radians(a0 + 90 * k / n)
            pts.append((qx + r * cos(t), qy + r * sin(t)))
    return pts


def mirror_x(pts):
    return [(2 * CX - p[0],) + tuple(p[1:]) for p in pts]


PARTS = {}   # name -> (object, bones it may bend with, outline px or 0)


def part(ob, bones, line=LINE):
    PARTS[ob.name] = (ob, bones, line)
    return ob


def seam(name, y, hw, hd, bones, x=CX, dc=0.0, gap=None, w=2.0):
    """An ink line drawn round a body at height y: where two parts meet at the same depth (a cuff
    under a sleeve, a hem band under the hoodie) the outlines cannot show, so the seam is drawn."""
    a0, a1, n = 0.0, 2 * pi, 40
    if gap:
        phi = asin(gap / hw)
        a0, a1 = -pi / 2 + phi, 3 * pi / 2 - phi
    pts = [(x + hw * cos(t), y, dc + hd * sin(t)) for t in (a0 + (a1 - a0) * i / n for i in range(n + 1))]
    ob = tube(name, pts, [w / 2] * len(pts), ['ink'], ref=Vector((0, 0, 1)), n=8, caps=(None, None) if not gap else (0.8, 0.8))
    return part(ob, bones, 0)


# ================================================================ HEAD
# Face rings: (y, half width, half depth, centre depth), measured inside the drawn outline.
HEAD = [(184, 30, 40, 6), (192, 42, 52, 5), (205, 49, 58, 3), (225, 51, 60, 1), (270, 51, 60, 0),
        (292, 48.5, 57, -1), (302, 47, 55, -2), (306, 45, 53, -2.5), (310, 43, 51, -3), (314, 41, 49, -4),
        (318, 39.5, 47, -5), (322, 36.5, 44, -6), (326, 33, 41, -7), (332, 27.5, 36, -9), (337, 21, 30, -10),
        (340, 15, 24, -11)]
head = loft('head', [hring(y, w, d, c, e=2.2) for y, w, d, c in HEAD], ['skin'],
            caps=(P(CX, 178, 6), P(CX, 342, -12)))
smooth(head)
part(head, ['head'])

for side in (-1, 1):
    ear = ellipsoid(f'ear.{"L" if side > 0 else "R"}', (CX + side * 56, 281, 4), (10, 19, 10), ['skin'],
                    rot=(0, 0, side * -18))
    smooth(ear, 1)
    part(ear, ['head'])

# Hair: the front is the drawing's own hair shape (traced), bulged into a dome over the head; curls
# behind give the back of the head its volume. Fused into one surface by a voxel remesh.
HAIR_BACK = [
    # (x, y, d, half width, half height, half depth), all hidden behind the face from the front
    (386, 214, 18, 54, 42, 58), (386, 252, 38, 50, 32, 38), (386, 280, 44, 44, 22, 26),
    (342, 262, 34, 16), (430, 262, 34, 16), (354, 284, 40, 14), (418, 284, 40, 14),
]


def slab(name, mask, depths, mat, smooth_iters=14):
    """A closed solid whose outline seen from the front is exactly `mask` (a drawing-px mask):
    front and back faces at depths(x, y) -> (front, back), walls round the outline, edges rounded
    a little by a voxel remesh."""
    UP = 2  # work on a 2x, slightly blurred mask so the outline is smooth, not pixel steps
    m = ndi.gaussian_filter(ndi.zoom(mask.astype(float), UP, order=1), 1.6) > 0.5
    step = 0.75
    ys, xs = np.nonzero(m)
    gx = np.arange(xs.min() / UP - 2, xs.max() / UP + 3, step)
    gy = np.arange(ys.min() / UP - 2, ys.max() / UP + 3, step)
    nx, ny = len(gx), len(gy)
    px = lambda v: min(int(round(v * UP)), m.shape[0] - 1)
    inside = np.array([[m[px(y), min(int(round(x * UP)), m.shape[1] - 1)] for x in gx] for y in gy])
    cell = inside[:-1, :-1] & inside[1:, :-1] & inside[:-1, 1:] & inside[1:, 1:]
    used = np.zeros_like(inside)
    for dj in (0, 1):
        for di in (0, 1):
            sub = np.zeros_like(inside)
            sub[dj:dj + ny - 1, di:di + nx - 1] = cell
            used |= sub
    verts, front_i, back_i = [], {}, {}
    for j in range(ny):
        for i in range(nx):
            if not used[j, i]:
                continue
            x, y = gx[i], gy[j]
            f, b = depths(x, y)
            front_i[i, j] = len(verts)
            verts.append(P(x, y, f))
            back_i[i, j] = len(verts)
            verts.append(P(x, y, b))
    faces, edges = [], {}
    for j in range(ny - 1):
        for i in range(nx - 1):
            if cell[j, i]:
                q = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
                faces.append(tuple(front_i[k] for k in q))
                faces.append(tuple(back_i[k] for k in q[::-1]))
                for a_, b_ in zip(q, q[1:] + q[:1]):
                    edges[(a_, b_)] = edges.get((a_, b_), 0) + 1
                    edges[(b_, a_)] = edges.get((b_, a_), 0)
    for (a_, b_), c in edges.items():  # the wall round the outline
        if c == 1 and edges.get((b_, a_), 0) == 0:
            faces.append((front_i[b_], front_i[a_], back_i[a_], back_i[b_]))
    ob = new_obj(name, verts, faces, [mat])
    fix_normals(ob)
    rm = ob.modifiers.new('fuse', 'REMESH')
    rm.mode = 'VOXEL'
    rm.voxel_size = 1.0 * S
    sm = ob.modifiers.new('soften', 'SMOOTH')
    sm.factor, sm.iterations = 1.0, smooth_iters
    dc = ob.modifiers.new('lighter', 'DECIMATE')
    dc.ratio = 0.25
    apply_mods(ob)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def tree_of(objs):
    """One ray-cast tree over several meshes' own surfaces (outline hulls left out)."""
    verts, polys = [], []
    for o in objs:
        me = o.data
        skip = [i for i, mt in enumerate(me.materials) if mt and mt.name == 'outline']
        base = len(verts)
        verts += [o.matrix_world @ v.co for v in me.vertices]
        polys += [[base + i for i in p.vertices] for p in me.polygons if p.material_index not in skip]
    return BVHTree.FromPolygons(verts, polys)


def hair_front():
    """The drawing's hair. Seen from the front its outline is exactly the drawing's (a solid cut to
    the drawing's hair shape, bulging into a dome over the forehead); all round the head it is a
    cap of curls, placed so that none of them shows past that outline from the front. The two are
    fused into one surface."""
    head_t = tree_of([head])
    mask = tr.hair_mask()

    def depths(x, y):
        k = max(0.12, 1 - ((x - 386) / 90) ** 2 - ((y - 228) / 76) ** 2)
        f = 6 - 74 * sqrt(k)
        h = head_t.ray_cast(P(x, y, -400), Vector((0, 1, 0)))
        if h[0] is not None:
            f = min(f, h[0].y / S - 3)
        return f, f + 34
    front = slab('hair', mask, depths, 'hair', smooth_iters=4)

    # under the curls, a scalp layer so the skull never shows between them (it sits inside the
    # front outline, or behind the face)
    pieces = [front, ellipsoid('scalp', (386, 238, 14), (54, 64, 62), ['hair'], n=32)]
    # the cap of curls: spread over a shell round the skull, each kept inside the front outline or
    # hidden behind the head, so the front view stays exactly the drawing's
    inside = ndi.binary_erosion(mask, tr.disk(2))
    golden = pi * (3 - sqrt(5))
    for i in range(520):
        z = 1 - 2 * (i + 0.5) / 520
        r_ = sqrt(1 - z * z)
        a_ = golden * i
        ux, uy, uz = r_ * cos(a_), z, r_ * sin(a_)     # uy up, uz back
        x, y, d = 386 + 62 * ux, 236 - 64 * uy, 12 + 66 * uz
        if y > 302 or (y > 258 and uz < 0.25) or uz < -0.4:
            continue
        for rad in (16 + 4 * max(0, uz), 12, 9):
            xs = np.arange(int(x - rad), int(x + rad) + 1)
            ys = np.arange(int(y - rad), int(y + rad) + 1)
            gx, gy = np.meshgrid(xs, ys)
            disc = (gx - x) ** 2 + (gy - y) ** 2 <= rad * rad
            gx, gy = gx[disc], gy[disc]
            in_mask = inside[gy, gx].all()
            behind_head = uz > 0.25 and abs(x - 386) + rad < 50 and y - rad > 185 and y + rad < 335
            if in_mask or behind_head:
                pieces.append(ellipsoid('curl', (x, y, d), (rad, rad, rad), ['hair'], n=12))
                break
    bpy.ops.object.select_all(action='DESELECT')
    for o in pieces:
        o.select_set(True)
    bpy.context.view_layer.objects.active = front
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    rm = ob.modifiers.new('fuse', 'REMESH')
    rm.mode = 'VOXEL'
    rm.voxel_size = 1.2 * S
    sm = ob.modifiers.new('soften', 'SMOOTH')
    sm.factor, sm.iterations = 1.0, 6
    dc = ob.modifiers.new('lighter', 'DECIMATE')
    dc.ratio = 0.3
    apply_mods(ob)
    ob.name = 'hair'
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


hair = hair_front()
part(hair, ['head'])

face_t = [head]

# Glasses: round-cornered frames standing a little off the face, temples back to the ears.
GLASS_D = -66
gl = []
for cx, w in ((359.5, 39.5), (413.0, 40.0)):
    pts = rrect(cx, 273, w, 30.5, 9.5)
    gl.append(tube('lens', [(x, y, GLASS_D + (abs(x - CX) - 25) * 0.18) for x, y in pts] + [(pts[0][0], pts[0][1], GLASS_D + (abs(pts[0][0] - CX) - 25) * 0.18)],
                   [1.9] * (len(pts) + 1), ['ink'], ref=Vector((0, 1, 0)), n=8, caps=(None, None)))
gl.append(tube('bridge', [(379, 266, -64), (386, 262.5, -65), (393, 266, -64)], [2.2] * 3, ['ink'], ref=Vector((0, 1, 0)), n=8))
for side, x0 in ((-1, 340), (1, 432.5)):
    gl.append(tube('temple', [(x0, 266, -58), (CX + side * 52, 264, -40), (CX + side * 54, 266, -10), (CX + side * 52, 272, 8)],
                   [2.0] * 4, ['ink'], ref=Vector((0, 0, 1)), n=8))
bpy.ops.object.select_all(action='DESELECT')
for o in gl:
    o.select_set(True)
bpy.context.view_layer.objects.active = gl[0]
bpy.ops.object.join()
glasses = bpy.context.view_layer.objects.active
glasses.name = 'glasses'
part(glasses, ['head'], 0)

# ================================================================ NECK, TEE, HOODIE
neck = loft('neck', [hring(y, 22, 20, 3) for y in (322, 340, 360, 382)], ['skin'], caps=(None, None))
smooth(neck)

part(neck, ['neck', 'head', 'chest'])

TEE = [(364, 27, 24, 4), (380, 46, 34, 3), (396, 66, 46, 2), (420, 76, 50, 0), (520, 76, 50, 0), (588, 75, 50, 0)]
tee = loft('tee', [hring(y, w, d, c) for y, w, d, c in TEE], ['tee'], caps=(None, P(CX, 592, 0)))
smooth(tee)
part(tee, ['hips', 'spine', 'chest'])

# tee neckline: a ribbed band around the base of the neck, lower at the front


def surf(rings, x, y, front=True):
    """Depth of a lofted surface (rings of (y, hw, hd, dc)) at drawing point x, y."""
    y = min(max(y, rings[0][0]), rings[-1][0])
    for (y0, w0, d0, c0), (y1, w1, d1, c1) in zip(rings, rings[1:]):
        if y0 <= y <= y1:
            f = (y - y0) / (y1 - y0)
            w, d, c = w0 + (w1 - w0) * f, d0 + (d1 - d0) * f, c0 + (c1 - c0) * f
            k = sqrt(max(0.0, 1 - ((x - CX) / w) ** 2))
            return c - d * k if front else c + d * k
    raise ValueError(y)


collar_pts = []
for i in range(29):
    t = 2 * pi * i / 28
    x, y = CX + 1 + 29 * cos(t), 364 - (22 if sin(t) < 0 else 4) * sin(t)  # the drawing's U neckline
    collar_pts.append((x, y, surf(TEE, x, y, sin(t) < 0) + (-1.2 if sin(t) < 0 else 1.2)))
collar = tube('collar', collar_pts, [2.0] * 29, ['ink'], ref=Vector((0, 0, 1)), n=8, caps=(None, None))
part(collar, ['chest', 'neck'], 0)

# Hoodie body: open at the front where the tee shows; the gap keeps its width all the way down.
GAP = 28.25
HOOD_BODY = [(366, 66, 46, 4), (380, 76, 51, 2), (400, 80, 54, 0), (450, 81, 55, 0),
             (520, 80, 55, 0), (577, 79, 55, 0)]
rings = []
for y, w, d, c in HOOD_BODY:
    phi = asin(min(0.95, GAP / w))
    rings.append(hring(y, w, d, c, n=33, a0=-pi / 2 + phi, a1=3 * pi / 2 - phi, closed=False))
hoodie = loft('hoodie', rings, ['hoodie'], closed=False)
smooth(hoodie)
solidify(hoodie, 3.0, 'hoodin')
part(hoodie, ['hips', 'spine', 'chest'])

rings = []
for y, w, d in ((576, 79, 56), (595, 78.5, 55.5)):
    phi = asin(GAP / w)
    rings.append(hring(y, w, d, 0, n=33, a0=-pi / 2 + phi, a1=3 * pi / 2 - phi, closed=False))
hem = loft('hem', rings, ['hoodie'], closed=False)
smooth(hem, 1)
solidify(hem, 4.0, 'hoodin')
part(hem, ['hips'])
seam('hem_top', 576.5, 81, 58, ['hips'], gap=GAP + 1, w=3.2)
# the front edges of the open hoodie (its rim is edge-on, so the outline cannot draw it)
for side in (-1, 1):
    x = CX + side * GAP
    d = -55 * sqrt(1 - (GAP / 81) ** 2) + 0.5
    part(tube(f'front_edge.{"L" if side > 0 else "R"}', [(x + side * 5, 392, d + 8), (x + side, 404, d + 1), (x, 420, d), (x, 500, d), (x, 596, d)],
              [2.6] * 5, ['ink'], ref=Vector((0, 1, 0)), n=8, caps=(0.6, 0.6)), ['hips', 'spine', 'chest'], 0)

# Hood: a thick rim around the neck, dark inside, with the lime piping on its outer edge.
# measured on the drawing: the rim's centre line, its radius, and its depth
HOOD = [(330, 334, -6, 8.5), (334, 324, 6, 8), (346, 318, 20, 7), (364, 315, 32, 6.5), (386, 314, 38, 6)]
hood_path = [h[:3] for h in HOOD] + mirror_x([h[:3] for h in HOOD[::-1]])[1:]
hood_r = [h[3] for h in HOOD] + [h[3] for h in HOOD[::-1]][1:]
neck_axis = P(CX, 0, 10)


def outward(i, c):
    r = Vector((c.x - neck_axis.x, c.y - neck_axis.y, 0))
    return r.normalized() if r.length > 1e-6 else Vector((0, 1, 0))


hood = tube('hood', hood_path, [(r, r + 2) for r in hood_r], ['hoodie'], ref=outward, n=16, caps=(0.5, 0.5))
smooth(hood)
def hood_paint(p, f):
    # by which way the face looks: away from the neck is the outside (lime piping along the top),
    # toward the neck is the dark lining
    c = P(*p)
    out = Vector((c.x - neck_axis.x, c.y - neck_axis.y, 0)).normalized()
    k = f.normal.dot(out)
    if k < -0.35:
        return 'navy'
    if k > 0.55 and 322 < p[1] < 358 and f.normal.z < 0.6:
        return 'lime'
    return None


paint(hood, hood_paint)
part(hood, ['chest', 'neck'])

inside = ellipsoid('hood_inside', (CX, 344, 18), (56, 30, 26), ['navy'])
smooth(inside, 1)
part(inside, ['chest', 'neck'])
back = ellipsoid('hood_back', (CX, 352, 52), (60, 40, 26), ['hoodie'], rot=(-12, 0, 0))
smooth(back, 1)
part(back, ['chest'])

for side, x in ((-1, 344), (1, 428)):
    nm = 'L' if side > 0 else 'R'
    s = tube(f'string.{nm}', [(x + side * 3, 386, -50), (x + side * 1, 400, -60), (x, 418, -60), (x, 428, -59)],
             [2.6] * 4, ['string'], ref=Vector((0, 1, 0)), n=10, caps=(0.8, 0.8))
    smooth(s, 1)
    paint(s, lambda p, f: 'ink' if p[1] > 424 else None)
    part(s, ['chest'], 1.6)

# ================================================================ ARMS (sleeves, cuffs, hands)
# Raglan sleeve from the hood down to the cuff, lime stripe down its outer side.
# Sleeve centre lines and radii fitted to the drawing's outlines (x, y, depth, radius), each side
# on its own: the drawing is not quite symmetric.
ARM = {
    'R': [(341, 358, -2, 8), (321, 367, 0, 18), (312, 378, 1, 25), (303, 386, 1, 27), (297, 398, 2, 27.5),
          (289.5, 416, 2, 27.5), (279.5, 440, 3, 26), (271, 470, 3, 25.5), (265.25, 506, 3, 25.75),
          (262, 530, 3, 25), (259.75, 554, 2, 24.25), (259.75, 566, 2, 22.75), (260.5, 574, 2, 19)],
    'L': [(431, 358, -2, 8), (451, 367, 0, 18), (463, 378, 1, 25), (472, 386, 1, 27), (478, 398, 2, 27.5),
          (486, 416, 2, 27.5), (495.5, 440, 3, 26), (504.5, 470, 3, 25.5), (510.25, 506, 3, 25.75),
          (513, 530, 3, 25), (515.25, 554, 2, 24.25), (515.25, 566, 2, 22.75), (515.25, 574, 2, 19.75)],
}
CUFF_X = {'R': 260, 'L': 515.5}


# Anatomical joint centres per side (drawing px: x, y, depth): the clavicle's inner end, the
# shoulder (ball of the humerus, inside the deltoid), the elbow and the wrist. Upper arm to forearm
# runs about 1.2 : 1, as on a real arm.
ARM_J = {
    'R': {'clav': (CX - 14, 372, 0), 'shoulder': (300, 390, 2), 'elbow': (266, 500, 5), 'wrist': (260, 596, 2)},
    'L': {'clav': (CX + 14, 372, 0), 'shoulder': (472, 390, 2), 'elbow': (509, 500, 5), 'wrist': (515.5, 596, 2)},
}
HAND_BONES = {}  # name -> (parent, head px, tail px, z axis hint in world space), filled by hand()


def arm(side):
    nm = 'L' if side > 0 else 'R'
    pts = [(x, y, d) for x, y, d, r in ARM[nm]]
    out = Vector((side, 0, 0))
    sl = tube(f'sleeve.{nm}', pts, [r for *_, r in ARM[nm]], ['hoodie'], ref=out, n=24, caps=(0.6, 0.3))
    smooth(sl)
    a = tube_angle(sl, out)

    def stripe(p, f):
        g, s_ = a(p)
        # angle 0 is straight out, +/-90 is front/back (v = t x u)
        front = -g if side < 0 else g
        return 'lime' if (s_ > 1.35 and -8 < front < 34) else None
    paint(sl, stripe)
    part(sl, [f'shoulder.{nm}', f'upper_arm.{nm}', f'forearm.{nm}', f'forearm_twist.{nm}', 'chest'])

    cx = CUFF_X[nm]
    cuff = loft(f'cuff.{nm}', [hring(y, r, r, 2, x=cx) for y, r in ((574, 17), (586, 16.5), (595, 16))], ['hoodie'],
                caps=(None, P(cx, 597, 2)))
    smooth(cuff)
    part(cuff, [f'forearm.{nm}', f'forearm_twist.{nm}'])
    seam(f'cuff_top.{nm}', 576, 18.5, 18.5, [f'forearm.{nm}', f'forearm_twist.{nm}'], x=cx, dc=2, w=3.2)

    hand(side, nm)


def wdir(v):
    """A direction in drawing px space (x, y down, depth) as a Blender vector."""
    return Vector((v.x, v.z, -v.y)).normalized()


def rot(v, axis, deg):
    """Rotate v about a unit axis (Rodrigues)."""
    a = radians(deg)
    return (v * cos(a) + axis.cross(v) * sin(a) + axis * axis.dot(v) * (1 - cos(a))).normalized()


def weigh(ob, bones):
    """Vertex weights by distance to a short chain of bones (px head/tail), blended at the joints."""
    segs = {b: (P(*h), P(*t)) for b, (h, t) in bones.items()}
    groups = {b: ob.vertex_groups.new(name=b) for b in bones}
    for v in ob.data.vertices:
        d = {b: max(seg_dist(v.co, *ab), 1e-6) for b, ab in segs.items()}
        w = {b: (1 / x) ** 10 for b, x in d.items()}
        tot = sum(w.values())
        for b, x in w.items():
            if x / tot > 0.01:
                groups[b].add([v.index], x / tot, 'REPLACE')


def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return (p - (a + ab * t)).length


def hand(side, nm, turn=55):
    """An anatomical hand, relaxed at the side: a palm with the knuckle arch, four fingers of three
    segments each and an opposable thumb, sized to the drawing's hand (wrist to fingertip about 10%
    of his height, as on a real person). Every finger has its own bones, so the hand can grip, point,
    wave or spread like a real one.

    Hand space (px): R toward the thumb, D out of the back of the hand, F toward the fingertips.
    Hanging, the palm faces the thigh, turned `turn` degrees toward the front (as drawn)."""
    th = radians(turn)
    Lat = Vector((side, 0, 0))   # away from the body
    Fr = Vector((0, 0, -1))      # toward the viewer
    F = Vector((0, 1, 0))        # down the arm
    D = Lat * cos(th) + Fr * sin(th)
    R = Fr * cos(th) - Lat * sin(th)
    W = Vector(ARM_J[nm]['wrist'])

    def H(r, d, f):
        return W + R * r + D * d + F * f
    t3 = lambda v: (v.x, v.y, v.z)
    Rw, Dw = wdir(R), wdir(D)
    hb = f'hand.{nm}'
    mcp_mid = H(3.7, 0, 33)
    HAND_BONES[hb] = (f'forearm.{nm}', t3(W), t3(mcp_mid), wdir(-D))
    pieces = []

    # palm: a rounded slab, wider and thinner toward the knuckles
    rings = []
    for f, hw, ht in ((-3, 11, 6.5), (5, 13, 7), (15, 15, 6.8), (25, 15.5, 6.2), (31, 15, 5.6)):
        rings.append(ring(P(*t3(H(0.5, -0.3, f))), Rw, Dw, hw * S, ht * S, 20, 3.0))
    palm = loft('palm', rings, ['skin'], caps=(P(*t3(H(0.5, 0, -6))), P(*t3(H(0.5, -0.5, 35)))))
    smooth(palm, 1)
    weigh(palm, {hb: (t3(W), t3(mcp_mid))})
    pieces.append(palm)

    # the curl bends a finger toward the palm (-D) about the thumb-side axis
    sgn = 1 if rot(F, R, 10).dot(D) < 0 else -1
    ssp = 1 if rot(F, D, 10).dot(R) > 0 else -1  # + spread fans toward the thumb
    FINGERS = [  # name, knuckle r, knuckle f, segment lengths, base radius, spread, curl at the 3 joints
        ('index', 11.2, 31, (16, 10.5, 8.5), 3.55, 5, (10, 20, 12)),
        ('middle', 3.7, 33, (17.5, 11.5, 9), 3.65, 1, (12, 22, 13)),
        ('ring', -3.7, 32, (16.5, 11, 8.5), 3.5, -3, (14, 24, 14)),
        ('pinky', -11, 29, (13, 8.5, 7.5), 3.1, -8, (16, 26, 16)),
    ]
    for name, r0, f0, lens, rad, spread, curl in FINGERS:
        mcp = H(r0, -0.6, f0)
        d = rot(F, D, ssp * spread)
        joints = [mcp]
        dirs = []
        for k in range(3):
            d = rot(d, R, sgn * curl[k])
            dirs.append(d)
            joints.append(joints[-1] + d * lens[k])
        path = [mcp - dirs[0] * 7, mcp]
        radii = [rad + 0.4, rad + 0.25]
        for k in range(3):
            path += [joints[k] + dirs[k] * lens[k] * 0.5, joints[k + 1]]
            radii += [rad * (0.97 - 0.05 * k), rad * (0.93 - 0.07 * k)]
        path[-1] = joints[3] - dirs[2] * 1.5
        ft = tube('finger', [t3(p) for p in path], radii, ['skin'], ref=wdir(R), n=12, caps=(0.5, 1.0))
        smooth(ft, 1)
        bones = {hb: (t3(W), t3(mcp_mid))}
        parent = hb
        for k in range(3):
            bn = f'f_{name}.{k + 1:02d}.{nm}'
            HAND_BONES[bn] = (parent, t3(joints[k]), t3(joints[k + 1]), wdir(-D))
            bones[bn] = (t3(joints[k]), t3(joints[k + 1]))
            parent = bn
        weigh(ft, bones)
        pieces.append(ft)

    # thumb: from its base by the wrist, lying alongside the index, turned toward the palm
    cmc = H(9, -3.5, 5)
    d0 = (F * 1.0 + R * 0.62 - D * 0.45).normalized()
    d1 = (d0 + F * 0.25 - R * 0.12).normalized()
    d2 = (d1 + F * 0.2 - R * 0.15).normalized()
    j = [cmc, cmc + d0 * 15, None, None]
    j[2] = j[1] + d1 * 11
    j[3] = j[2] + d2 * 9
    path = [cmc - d0 * 3, cmc, (cmc + j[1]) / 2, j[1], (j[1] + j[2]) / 2, j[2], (j[2] + j[3]) / 2, j[3] - d2 * 1.5]
    radii = [5.8, 6.0, 5.6, 4.5, 4.3, 4.1, 3.9, 3.6]
    tb = tube('thumb', [t3(p) for p in path], radii, ['skin'], ref=wdir(-D), n=12, caps=(0.5, 1.0))
    smooth(tb, 1)
    bones = {hb: (t3(W), t3(mcp_mid))}
    parent = hb
    for k in range(3):
        bn = f'f_thumb.{k + 1:02d}.{nm}'
        HAND_BONES[bn] = (parent, t3(j[k]), t3(j[k + 1]), wdir(-D))
        bones[bn] = (t3(j[k]), t3(j[k + 1]))
        parent = bn
    weigh(tb, bones)
    pieces.append(tb)

    bpy.ops.object.select_all(action='DESELECT')
    for o in pieces:
        o.select_set(True)
    bpy.context.view_layer.objects.active = pieces[0]
    bpy.ops.object.join()
    h = bpy.context.view_layer.objects.active
    h.name = f'hand.{nm}'
    part(h, None)  # weighted above, finger by finger


arm(-1)
arm(1)


def hood_front():
    """The hood's rim and lining in front, taken from the drawing: its shape, and per face the
    drawing's own colour there (green rim, lime piping, navy lining)."""
    under = tree_of([PARTS[n][0] for n in PARTS if n.startswith(('neck', 'tee', 'hoodie', 'hood_inside', 'sleeve', 'hood'))
                     and PARTS[n][2]])

    mask = tr.hood_mask()
    # depth of whatever lies under the hood, then made smooth (a fold of fabric, not a stack of
    # steps) while staying in front of everything under it
    ys, xs = np.nonzero(ndi.binary_dilation(mask, tr.disk(10)))
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    raw = np.full((y1 - y0, x1 - x0), np.nan)
    for y in range(y0, y1):
        for x in range(x0, x1):
            h = under.ray_cast(P(x, y, -400), Vector((0, 1, 0)))
            if h[0] is not None:
                raw[y - y0, x - x0] = h[0].y / S
    raw = np.where(np.isnan(raw), np.nanmax(raw), raw)
    front = ndi.gaussian_filter(ndi.minimum_filter(raw, 15), 5) - 5

    def depths(x, y):
        f = front[min(max(int(round(y)) - y0, 0), y1 - y0 - 1), min(max(int(round(x)) - x0, 0), x1 - x0 - 1)]
        return f, f + 14
    ob = slab('hood_front', mask, depths, 'hoodie', smooth_iters=6)
    part(ob, ['chest', 'neck'])


hood_front()

# ================================================================ LEGS
# Each leg of the trousers runs from the waist (half of the hips) to the ankle, so there is no
# hip-to-leg junction to show; the two halves fuse down the middle above the crotch.
LEGS = [(588, 38, 41, 50, 2.6), (606, 40, 40, 48, 2.6), (620, 44, 34, 38, 2.3), (634, 46, 31, 33, 2.1),
        (700, 46, 29.5, 28, 2), (760, 49, 25.5, 25, 2), (810, 52, 23.5, 23, 2), (829, 53, 23, 22.5, 2)]
legs = []
for side in (-1, 1):
    leg = loft('leg', [hring(y, w, d, 0, x=CX + side * o, n=24, e=e) for y, o, w, d, e in LEGS], ['pants'],
               caps=(P(CX + side * 38, 584, 0), P(CX + side * 54, 832, 0)))
    smooth(leg)
    legs.append(leg)
pelvis = legs[0]
# one pants surface, rounded where the legs meet the hips so no crease line shows
bpy.ops.object.select_all(action='DESELECT')
for o in legs:
    o.select_set(True)
bpy.context.view_layer.objects.active = pelvis
bpy.ops.object.join()
pelvis = bpy.context.view_layer.objects.active
rm = pelvis.modifiers.new('fuse', 'REMESH')
rm.mode = 'VOXEL'
rm.voxel_size = 1.5 * S
sm = pelvis.modifiers.new('soften', 'SMOOTH')
sm.factor, sm.iterations = 0.8, 10
dc = pelvis.modifiers.new('lighter', 'DECIMATE')
dc.ratio = 0.25
apply_mods(pelvis)
pelvis.name = 'pants'
for p in pelvis.data.polygons:
    p.use_smooth = True
part(pelvis, ['hips', 'thigh.L', 'thigh.R', 'shin.L', 'shin.R'])


def shoe(side):
    """Rounded shoe with a flat sole, heel under the ankle, toes turned out like the drawing's."""
    nm = 'L' if side > 0 else 'R'
    yaw = side * 45
    ob = ellipsoid(f'shoe.{nm}', (CX, FLOOR, 0), (26, 16.5, 50), ['shoe'])
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    for v in bm.verts:
        z = v.co.z
        if z < -10 * S:  # flatten the sole
            v.co.z = -10 * S + (z + 10 * S) * 0.15
        if v.co.y < 0:   # toe box a bit fuller than the heel
            v.co.x *= 1.08
    bm.to_mesh(ob.data)
    bm.free()
    ob.rotation_euler = (0, 0, radians(yaw))
    ob.location = P(CX + side * 76, 845, -14)
    apply_transform(ob)
    smooth(ob, 1)
    part(ob, [f'foot.{nm}'])


shoe(-1)
shoe(1)

# ground shadow (not part of the character)
sh = ellipsoid('shadow', (CX + 3, 866, -10), (163, 0.5, 150), ['shadow'])

# ================================================================ RIG
# A human skeleton placed at the anatomical joint centres inside the mesh (drawing px: head, tail).
# Every bone's local axes are set so the joints bend like a person's: Y runs along the bone and
# X is the hinge axis, so elbows, knees, wrists and finger joints all flex about X (positive bends
# them the natural way). ".L" is the character's left (+X).
BONES = {
    'root': (None, (CX, FLOOR, 0), (CX, FLOOR, 60)),
    'hips': ('root', (CX, 604, 4), (CX, 545, 4)),
    'spine': ('hips', (CX, 545, 4), (CX, 470, 2)),
    'chest': ('spine', (CX, 470, 2), (CX, 380, 4)),
    'neck': ('chest', (CX, 380, 4), (CX, 338, 2)),
    'head': ('neck', (CX, 338, 2), (CX, 172, 2)),
}
for side, sx in (('L', 1), ('R', -1)):
    X = lambda o: CX + sx * o
    J = ARM_J[side]
    ew = Vector(J['elbow']).lerp(Vector(J['wrist']), 0.5)
    BONES.update({
        f'shoulder.{side}': ('chest', J['clav'], J['shoulder']),
        f'upper_arm.{side}': (f'shoulder.{side}', J['shoulder'], J['elbow']),
        f'forearm.{side}': (f'upper_arm.{side}', J['elbow'], J['wrist']),
        # the lower half of the forearm turns with the hand (pronation), so the wrist never wrings
        f'forearm_twist.{side}': (f'forearm.{side}', tuple(ew), J['wrist']),
        f'thigh.{side}': ('hips', (X(44), 614, 0), (X(47), 726, -3)),
        f'shin.{side}': (f'thigh.{side}', (X(47), 726, -3), (X(53), 832, 3)),
        f'foot.{side}': (f'shin.{side}', (X(53), 832, 3), (X(53 + 30), 856, 3 - 30)),
    })
for n, (parent, h, t, z) in HAND_BONES.items():
    BONES[n] = (parent, h, t)
# animation controls (not deforming)
CONTROLS = {}
for side, sx in (('L', 1), ('R', -1)):
    X = lambda o: CX + sx * o
    J = ARM_J[side]
    CONTROLS.update({
        # same rest as the foot, so the foot can copy it exactly (stays flat on the floor)
        f'foot_ik.{side}': ('root', (X(53), 832, 3), (X(53 + 30), 856, 3 - 30)),
        f'knee_pole.{side}': ('root', (X(47), 726, -160), (X(47), 726, -200)),
        f'hand_ik.{side}': ('root', J['wrist'], HAND_BONES[f'hand.{side}'][2]),
        f'elbow_pole.{side}': ('root', (J['elbow'][0], J['elbow'][1], 140), (J['elbow'][0], J['elbow'][1], 180)),
    })

# Joint ranges (degrees, local X/Y/Z): how far a person's joints actually go.
LIMITS = {
    'forearm': ((0, 150), (0, 0), (-4, 4)),          # elbow: a hinge, no hyperextension
    'forearm_twist': (None, None, None),
    'hand': ((-70, 80), (-85, 85), (-25, 35)),       # wrist: flex/extend, pronate/supinate, tilt
    'shin': ((-150, 0), (0, 0), (-3, 3)),            # knee: a hinge that bends back
    'foot': ((-45, 30), (-20, 20), (-25, 25)),
    'neck': ((-40, 35), (-50, 50), (-30, 30)),
    'head': ((-35, 30), (-45, 45), (-25, 25)),
    'f_thumb.01': ((-25, 50), (-30, 30), (-35, 35)),
    'f_thumb.02': ((-10, 60), (0, 0), (-5, 5)),
    'f_thumb.03': ((-15, 85), (0, 0), (0, 0)),
}
for f in ('index', 'middle', 'ring', 'pinky'):
    LIMITS[f'f_{f}.01'] = ((-20, 90), (0, 0), (-18, 18))  # knuckle: curls and spreads
    LIMITS[f'f_{f}.02'] = ((0, 105), (0, 0), (0, 0))      # finger joints: hinges
    LIMITS[f'f_{f}.03'] = ((-5, 80), (0, 0), (0, 0))


def build_rig():
    arm = bpy.data.armatures.new('doodle_rig')
    arm.display_type = 'OCTAHEDRAL'
    rig = bpy.data.objects.new('doodle_rig', arm)
    COL.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.edit_bones
    for name, (parent, h, t) in list(BONES.items()) + list(CONTROLS.items()):
        b = eb.new(name)
        b.head, b.tail = P(*h), P(*t)
        b.use_deform = name in BONES and name != 'root'
        if parent:
            b.parent = eb[parent]
            b.use_connect = name in BONES and (eb[parent].tail - b.head).length < 1e-6
    for b in eb:
        if b.name in HAND_BONES:
            b.align_roll(HAND_BONES[b.name][3])  # Z to the palm: + X rotation curls
        elif b.name.startswith('hand_ik'):
            b.align_roll(HAND_BONES[b.name.replace('hand_ik', 'hand')][3])
        elif abs((b.tail - b.head).normalized().y) < 0.9:
            b.align_roll(Vector((0, -1, 0)))     # Z forward: + X bends elbows forward
    bpy.ops.object.mode_set(mode='POSE')
    pb = rig.pose.bones
    for b in pb:
        b.rotation_mode = 'XYZ'
        key = b.name.rsplit('.', 1)[0] if b.name.count('.') else b.name
        lim = LIMITS.get(key)
        if lim and any(lim):
            c = b.constraints.new('LIMIT_ROTATION')
            c.owner_space = 'LOCAL'
            c.use_transform_limit = True
            for ax, rng in zip('xyz', lim):
                if rng is None:
                    continue
                setattr(c, f'use_limit_{ax}', True)
                setattr(c, f'min_{ax}', radians(rng[0]))
                setattr(c, f'max_{ax}', radians(rng[1]))
    for side in ('L', 'R'):
        # forearm twist follows the hand's turn about the forearm
        c = pb[f'forearm_twist.{side}'].constraints.new('COPY_ROTATION')
        c.target, c.subtarget = rig, f'hand.{side}'
        c.use_x, c.use_y, c.use_z = False, True, False
        c.target_space = c.owner_space = 'LOCAL'
        # legs: IK to the foot control, knee aimed by its pole; knees only hinge
        ik = pb[f'shin.{side}'].constraints.new('IK')
        ik.target, ik.subtarget = rig, f'foot_ik.{side}'
        ik.pole_target, ik.pole_subtarget = rig, f'knee_pole.{side}'
        ik.pole_angle = radians(POLE.get(f'shin.{side}', 90))
        ik.chain_count = 2
        c = pb[f'foot.{side}'].constraints.new('COPY_ROTATION')  # planted feet stay flat
        c.target, c.subtarget = rig, f'foot_ik.{side}'
        sh = pb[f'shin.{side}']
        sh.lock_ik_y = sh.lock_ik_z = True
        sh.use_ik_limit_x = True
        sh.ik_min_x, sh.ik_max_x = radians(-150), 0
        # arms: FK by default; the IK is there to switch on (influence) for pushes and grabs
        ik = pb[f'forearm.{side}'].constraints.new('IK')
        ik.target, ik.subtarget = rig, f'hand_ik.{side}'
        ik.pole_target, ik.pole_subtarget = rig, f'elbow_pole.{side}'
        ik.pole_angle = radians(POLE.get(f'forearm.{side}', -90))
        ik.chain_count = 2
        ik.influence = 0.0
        c = pb[f'hand.{side}'].constraints.new('COPY_ROTATION')  # with the IK on, the hand follows its control
        c.name = 'hand_ik'
        c.target, c.subtarget = rig, f'hand_ik.{side}'
        c.influence = 0.0
        fa = pb[f'forearm.{side}']
        fa.lock_ik_y = fa.lock_ik_z = True
        fa.use_ik_limit_x = True
        fa.ik_min_x, fa.ik_max_x = 0, radians(150)
    bpy.ops.object.mode_set(mode='OBJECT')
    return rig


# IK pole angles that keep the rest pose exactly (found by search, see find_poles)
POLE = {}


def find_poles(rig):
    """Pole angle per IK chain that leaves the rest pose untouched."""
    pb = rig.pose.bones
    for ikb, chain in (('shin', 'thigh'), ('forearm', 'upper_arm')):
        for side in ('L', 'R'):
            c = pb[f'{ikb}.{side}'].constraints['IK']
            inf = c.influence
            c.influence = 1.0
            best = None
            for a10 in range(-1800, 1800, 5):
                c.pole_angle = radians(a10 / 10)
                bpy.context.view_layer.update()
                err = sum(sum(abs(x) for r in (pb[f'{b}.{side}'].matrix.to_3x3() - rig.data.bones[f'{b}.{side}'].matrix_local.to_3x3()) for x in r)
                          for b in (chain, ikb))
                if best is None or err < best[0]:
                    best = (err, a10 / 10)
            c.pole_angle = radians(best[1])
            c.influence = inf
            POLE[f'{ikb}.{side}'] = best[1]
    bpy.context.view_layer.update()


def skin(rig):
    """Weights by distance to the bones each part may bend with (smooth blends at the joints); the
    forearm's weight shades into its twist bone toward the wrist. Hands come pre-weighted."""
    segs = {n: (P(*h), P(*t)) for n, (_, h, t) in BONES.items()}
    for name, (ob, bones, line) in PARTS.items():
        if bones is not None:
            groups = {b: ob.vertex_groups.new(name=b) for b in bones}
            for v in ob.data.vertices:
                if len(bones) == 1:
                    groups[bones[0]].add([v.index], 1.0, 'REPLACE')
                    continue
                d = {b: max(seg_dist(v.co, *segs[b]), 1e-5) for b in bones if not b.startswith('forearm_twist')}
                w = {b: (1 / x) ** 8 for b, x in d.items()}
                tot = sum(w.values())
                w = {b: x / tot for b, x in w.items()}
                for side in ('L', 'R'):
                    fa, tw = f'forearm.{side}', f'forearm_twist.{side}'
                    if fa in w and tw in bones:
                        a, b = segs[fa]
                        t = max(0.0, min(1.0, (v.co - a).dot(b - a) / (b - a).length_squared))
                        k = t * t * (3 - 2 * t)
                        w[tw] = w[fa] * k
                        w[fa] *= 1 - k
                for b, x in w.items():
                    if x > 0.01:
                        groups[b].add([v.index], x, 'REPLACE')
        mod = ob.modifiers.new('rig', 'ARMATURE')
        mod.object = rig
        mod.use_deform_preserve_volume = True  # no "candy wrapper" when a joint twists
        ob.parent = rig


# ================================================================ OUTLINES
OUTLINE = outline_mat()


def add_hull(ob, px):
    me = ob.data
    me.materials.append(OUTLINE)
    k = len(me.materials) - 1
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()
    nrm = {v: v.normal.copy() for v in bm.verts}
    old = list(bm.verts)
    ret = bmesh.ops.duplicate(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces))
    vmap = ret['vert_map']
    for v in old:
        nv = vmap[v]
        nv.co = v.co + nrm[v] * (px * S)
    nf = [f for f in ret['geom'] if isinstance(f, bmesh.types.BMFace)]
    bmesh.ops.reverse_faces(bm, faces=nf)
    for f in nf:
        f.material_index = k
    bm.to_mesh(me)
    bm.free()


def finish_outlines():
    for name, (ob, bones, line) in PARTS.items():
        if line:
            add_hull(ob, line)


# ================================================================ RENDER
def setup_render(res=(776, 1024)):
    SC.render.engine = 'CYCLES'
    SC.cycles.device = 'CPU'
    SC.cycles.samples = 24
    SC.cycles.max_bounces = 0
    SC.cycles.transparent_max_bounces = 24
    SC.cycles.use_denoising = False
    SC.cycles.filter_width = 1.0
    SC.render.film_transparent = True
    SC.view_settings.view_transform = 'Standard'
    SC.view_settings.look = 'None'
    SC.render.resolution_x, SC.render.resolution_y = res
    SC.render.resolution_percentage = 100


def camera(name, yaw=0.0, pitch=0.0, res=(776, 1024), centre=(388, 512), scale_px=1024):
    """Orthographic camera; yaw turns around the figure (degrees, + shows his left side)."""
    cam = bpy.data.objects.get('cam') or bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    if cam.name not in SC.collection.objects:
        SC.collection.objects.link(cam)
    SC.camera = cam
    cam.data.type = 'ORTHO'
    cam.data.sensor_fit = 'VERTICAL'
    cam.data.ortho_scale = scale_px * S
    cam.data.clip_end = 100
    target = P(centre[0], centre[1], 0)
    rot = Matrix.Rotation(radians(yaw), 4, 'Z') @ Matrix.Rotation(radians(pitch), 4, 'X')
    back = rot @ Vector((0, -20, 0))
    cam.location = target + back
    cam.rotation_euler = (rot @ Matrix.Rotation(radians(90), 4, 'X')).to_euler()
    setup_render(res)
    SC.render.filepath = os.path.join(OUT, name + '.png')
    bpy.ops.render.render(write_still=True)


def traced_lines():
    """Every ink line of the drawing that the model's outlines miss (face, strands, folds, seams),
    taken from the drawing pixel for pixel and laid onto the surface it falls on, so it moves with
    that part. Lines over the hands are left out: the hands are modelled as real hands, not as drawn."""
    tmp = os.path.join(OUT, '_pass1.png')
    camera('_pass1', pitch=0.0)
    miss = tr.missing_lines(tmp)
    os.remove(tmp)
    targets = {}
    for name, (ob, bones, line) in PARTS.items():
        if line == 0 and name not in ('glasses',):
            continue
        targets[name] = tree_of([ob])
    lab, n = ndi.label(miss)
    per = {}
    for i, sl in enumerate(ndi.find_objects(lab)):
        ys, xs = np.nonzero(lab[sl] == i + 1)
        ys, xs = ys + sl[0].start, xs + sl[1].start
        votes = {}
        for k in np.linspace(0, len(xs) - 1, min(len(xs), 9)).astype(int):
            hs = [(nm_, t.ray_cast(P(xs[k], ys[k], -400), Vector((0, 1, 0)))) for nm_, t in targets.items()]
            hs = [(nm_, h) for nm_, h in hs if h[0] is not None]
            if hs:
                nm_ = min(hs, key=lambda nh: nh[1][3])[0]
                votes[nm_] = votes.get(nm_, 0) + 1
        if not votes:
            continue
        hit = max(votes, key=votes.get)
        if hit.startswith('hand.'):
            continue
        per.setdefault(hit, np.zeros_like(miss))
        per[hit] |= lab == i + 1
    for name, m in per.items():
        raster_decal(f'lines.{name}', m, targets[name], 'ink', 0.8, PARTS[name][1])

    # the drawing's flat colour patches: shading under the chin, in the ears and below the collar,
    # and the hood's lining and piping, each laid onto the part it falls on
    global CLS
    if CLS is None:
        CLS = tr.colour_class(tr.rgb())
    WHERE = {'shade': ('head', 'neck', 'ear.L', 'ear.R', 'tee'), 'navy': ('hood_front',), 'lime': ('hood_front', 'hood', 'sleeve.L', 'sleeve.R')}
    for cls_, allowed in WHERE.items():
        ys, xs = np.nonzero(CLS == cls_)
        masks = {}
        for x, y in zip(xs, ys):
            hs = [(nm_, t.ray_cast(P(x, y, -400), Vector((0, 1, 0)))) for nm_, t in targets.items()]
            hs = [(nm_, h) for nm_, h in hs if h[0] is not None]
            if not hs:
                continue
            nm_ = min(hs, key=lambda nh: nh[1][3])[0]
            if nm_ == 'head' and y < 290:  # (anti-aliasing at the fringe reads as shade: not shading)
                continue
            if nm_ in allowed:
                masks.setdefault(nm_, np.zeros(CLS.shape, bool))[y, x] = True
        for nm_, m in masks.items():
            m = ndi.binary_opening(ndi.binary_closing(m, tr.disk(1)), tr.disk(1))
            raster_decal(f'{cls_}.{nm_}', m, targets[nm_], cls_, 0.4, PARTS[nm_][1])


def raster_decal(name, m, tree, mat, lift, bones, UP=2):
    """A drawing-px mask as a fine grid of little quads laid onto a surface (dropped along the view
    axis), `lift` px off it; leaves out what lies on faces seen edge-on (they would smear)."""
    big = ndi.gaussian_filter(ndi.zoom(m.astype(float), UP, order=1), 0.7) > 0.45
    ys, xs = np.nonzero(big)
    if not len(xs):
        return
    idx, verts, faces, facing = {}, [], [], []

    def vid(i, j):
        if (i, j) not in idx:
            x, y = i / UP - 0.25, j / UP - 0.25
            h = tree.ray_cast(P(x, y, -400), Vector((0, 1, 0)))
            idx[i, j] = len(verts)
            verts.append([x, y, h[0].y if h[0] is not None else None])
            facing.append(-h[1].y if h[0] is not None else 0.0)
        return idx[i, j]
    for j, i in zip(ys, xs):
        faces.append((vid(i, j), vid(i + 1, j), vid(i + 1, j + 1), vid(i, j + 1)))
    known = [v[2] for v in verts if v[2] is not None]
    fill = sum(known) / len(known) if known else 0.0
    co = [Vector((P(x, y).x, (d if d is not None else fill) - lift * S, P(x, y).z)) for x, y, d in verts]
    faces = [f for f in faces if sum(facing[k] for k in f) / 4 >= 0.3]
    ob = new_obj(name, co, faces, [mat])
    for p in ob.data.polygons:
        p.use_smooth = False
    fix_facing(ob)
    part(ob, bones, 0)


def export_glb(path):
    """Skinned GLB for three.js: deforming bones only, flat colours as unlit materials."""
    for ob in SC.objects:
        ob.select_set(ob.name in PARTS or ob.name == 'doodle_rig')
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_skins=True,
                              export_def_bones=True, export_animations=False, export_apply=False,
                              export_yup=True)


if __name__ == '__main__':
    finish_outlines()
    traced_lines()
    RIG = build_rig()
    find_poles(RIG)
    skin(RIG)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'doodle.blend'))
    if '--glb' in sys.argv:
        export_glb(os.path.join(OUT, 'doodle.glb'))
    if '--render' in sys.argv:
        camera('front')
        camera('three_quarter', yaw=-35, pitch=-6)
        camera('side', yaw=-90, pitch=-6)
        camera('back', yaw=180, pitch=-6)
