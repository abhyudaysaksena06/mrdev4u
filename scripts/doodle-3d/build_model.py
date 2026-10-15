# Builds the doodle character (scripts/doodle-trace/reference.png) as a rigged 3D toon model.
#
#   pip install bpy==5.2.2          # Blender as a Python module, runs headless
#   python3 build_model.py <out_dir> [--render] [--glb]
#
# Writes <out_dir>/doodle.blend, plus front/three-quarter/side/back renders with --render and
# <out_dir>/doodle.glb (skinned, for three.js) with --glb. The committed doodle.blend next to this
# script is its output; preview/ has the turnaround and a rig test.
#
# Rig: root > hips > spine > chest > neck > head, shoulder > upper_arm > forearm > hand and
# thigh > shin > foot per side. Legs are IK (foot_ik, knee_pole controls); arms are FK with an IK
# (hand_ik, elbow_pole) ready to switch on through the constraint's influence.
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
        (292, 49, 57, -1), (304, 46, 53, -2), (316, 41, 47, -4), (326, 34, 40, -7), (334, 25, 31, -9),
        (339, 14, 20, -11)]
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
import trace as tr
from scipy import ndimage as ndi

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
    """The drawing's hair: its outline exactly the drawing's, its volume a rounded envelope round
    the skull, always just in front of the face where the fringe covers it."""
    head_t = tree_of([head])

    def depths(x, y):
        k = max(0.12, 1 - ((x - 386) / 90) ** 2 - ((y - 228) / 76) ** 2)
        f = 6 - 74 * sqrt(k)
        b = 6 + 72 * sqrt(k)
        h = head_t.ray_cast(P(x, y, -400), Vector((0, 1, 0)))
        if h[0] is not None:
            f = min(f, h[0].y / S - 3)
        return f, b
    return slab('hair', tr.hair_mask(), depths, 'hair')


hair = hair_front()
curls = []
for h in HAIR_BACK:
    x, y, d = h[:3]
    r = h[3:] if len(h) == 6 else (h[3], h[3], h[3])
    c = ellipsoid('curl', (x, y, d), r, ['hair'], n=20)
    smooth(c, 1)
    curls.append(c)
bpy.ops.object.select_all(action='DESELECT')
for c in curls:
    c.select_set(True)
hair.select_set(True)
bpy.context.view_layer.objects.active = hair
bpy.ops.object.join()
hair = bpy.context.view_layer.objects.active
hair.name = 'hair'
for p in hair.data.polygons:
    p.use_smooth = True
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
paint(neck, lambda p, f: 'shade' if p[1] < 350 else None)
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
    part(sl, [f'shoulder.{nm}', f'upper_arm.{nm}', f'forearm.{nm}', 'chest'])

    cx = CUFF_X[nm]
    cuff = loft(f'cuff.{nm}', [hring(y, r, r, 2, x=cx) for y, r in ((574, 17), (586, 16.5), (595, 16))], ['hoodie'],
                caps=(None, P(cx, 597, 2)))
    smooth(cuff)
    part(cuff, [f'forearm.{nm}'])
    seam(f'cuff_top.{nm}', 576, 18.5, 18.5, [f'forearm.{nm}'], x=cx, dc=2, w=3.2)

    hand(side, nm, cx)


def hand(side, nm, cx, turn=18):
    """Relaxed hand hanging from the wrist, back of the hand to the front, thumb on the inner side.

    Built in hand space (px): X across the knuckles from little finger to index, Y out of the back
    of the hand, Z up the arm; the wrist is the origin. turn swings it toward the leg.
    """
    th = radians(turn)
    X = Vector((-side * cos(th), -sin(th), 0))   # (px x, depth) directions
    Y = Vector((side * sin(th), -cos(th), 0))
    wrist = Vector((cx, 2, 0))  # (px x, depth)

    def H(x, y, z):
        w = wrist + X * x + Y * y
        return (w.x, 596 - z, w.y)
    Xw = Vector((X.x, X.y, 0))  # the same direction in Blender space (px depth is world y)
    pieces = [tube('palm', [H(0, 0, 4), H(0, 0, -6), H(0, -1, -20), H(0, -2, -30)],
                   [(17, 8), (21, 9), (22, 9.5), (21.5, 9)], ['skin'], ref=Xw, n=16, e=2.6, caps=(0.5, 0.4))]
    # little finger to index: knuckle x, length, spread
    for fx, fl, sp, fd in ((-17.5, 26, -3, 1.5), (-6, 32, -1, 0.5), (6, 33, 1, -0.5), (17.5, 29, 3, -1.5)):
        k = H(fx, -2 + fd, -28)
        mid = H(fx + sp * 0.5, -3 + fd, -28 - fl * 0.55)
        tip = H(fx + sp, -8 + fd, -28 - fl)
        pieces.append(tube('finger', [k, mid, tip], [4.6, 4.3, 3.9], ['skin'], ref=Xw, n=12, caps=(0.5, 0.95)))
    pieces.append(tube('thumb', [H(19, -6, -8), H(26, -12, -22), H(28, -15, -36)], [6.2, 5.4, 4.8], ['skin'],
                       ref=Xw, n=12, caps=(0.5, 0.95)))
    for o in pieces:
        smooth(o, 1)
    bpy.ops.object.select_all(action='DESELECT')
    for o in pieces:
        o.select_set(True)
    bpy.context.view_layer.objects.active = pieces[0]
    bpy.ops.object.join()
    h = bpy.context.view_layer.objects.active
    h.name = f'hand.{nm}'
    part(h, [f'hand.{nm}'])


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
    cls = tr.colour_class(tr.rgb())

    def colour(p, f):
        if f.normal.y > -0.6:  # only what faces the viewer takes the drawing's colours
            return None
        x, y = int(round(p[0])), int(round(p[1]))
        c = cls[y, x]
        return {'lime': 'lime', 'navy': 'navy'}.get(c)
    paint(ob, colour)
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
# Bones in drawing px (head, tail), roll toward the viewer. ".L" is the character's left (+X).
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
    BONES.update({
        f'shoulder.{side}': ('chest', (X(14), 372, 0), (X(80), 392, 2)),
        f'upper_arm.{side}': (f'shoulder.{side}', (X(80), 392, 2), (X(123), 488, 6)),
        f'forearm.{side}': (f'upper_arm.{side}', (X(123), 488, 6), (X(125), 592, 2)),
        f'hand.{side}': (f'forearm.{side}', (X(125), 592, 2), (X(126), 652, -4)),
        f'thigh.{side}': ('hips', (X(42), 612, 0), (X(48), 724, -3)),
        f'shin.{side}': (f'thigh.{side}', (X(48), 724, -3), (X(54), 832, 4)),
        f'foot.{side}': (f'shin.{side}', (X(54), 832, 4), (X(100), 856, -34)),
    })
# animation controls (not exported as deforming bones)
CONTROLS = {}
for side, sx in (('L', 1), ('R', -1)):
    X = lambda o: CX + sx * o
    CONTROLS.update({
        f'foot_ik.{side}': ('root', (X(54), 832, 4), (X(54), 832, 50)),
        f'knee_pole.{side}': ('root', (X(48), 724, -160), (X(48), 724, -200)),
        f'hand_ik.{side}': ('root', (X(125), 592, 2), (X(125), 592, 40)),
        f'elbow_pole.{side}': ('root', (X(123), 488, 140), (X(123), 488, 180)),
    })


def build_rig():
    arm = bpy.data.armatures.new('doodle_rig')
    arm.display_type = 'STICK'
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
    # roll so every bone's Z points toward the viewer (-Y): predictable local axes for animation
    for b in eb:
        if abs((b.tail - b.head).normalized().y) < 0.9:
            b.align_roll(Vector((0, -1, 0)))
    bpy.ops.object.mode_set(mode='POSE')
    pb = rig.pose.bones
    for side in ('L', 'R'):
        # legs: IK to the foot control with the knee aimed by its pole (feet stay planted)
        ik = pb[f'shin.{side}'].constraints.new('IK')
        ik.target, ik.subtarget = rig, f'foot_ik.{side}'
        ik.pole_target, ik.pole_subtarget = rig, f'knee_pole.{side}'
        ik.pole_angle = radians(90)  # found by search: keeps the rest pose exactly
        ik.chain_count = 2
        # arms: FK by default; the IK is there to switch on (influence) for pushes and grabs
        ik = pb[f'forearm.{side}'].constraints.new('IK')
        ik.target, ik.subtarget = rig, f'hand_ik.{side}'
        ik.pole_target, ik.pole_subtarget = rig, f'elbow_pole.{side}'
        ik.pole_angle = radians(-99 if side == 'L' else -81)
        ik.chain_count = 2
        ik.influence = 0.0
    bpy.ops.object.mode_set(mode='OBJECT')
    return rig


def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return (p - (a + ab * t)).length


def skin(rig):
    """Weights by distance to the bones each part may bend with (smooth blends at the joints)."""
    heads = {n: (P(*h), P(*t)) for n, (_, h, t) in BONES.items()}
    for name, (ob, bones, line) in PARTS.items():
        groups = {b: ob.vertex_groups.new(name=b) for b in bones}
        for v in ob.data.vertices:
            if len(bones) == 1:
                groups[bones[0]].add([v.index], 1.0, 'REPLACE')
                continue
            d = {b: max(seg_dist(v.co, *heads[b]), 1e-5) for b in bones}
            w = {b: (1 / x) ** 8 for b, x in d.items()}
            tot = sum(w.values())
            for b, x in w.items():
                if x / tot > 0.01:
                    groups[b].add([v.index], x / tot, 'REPLACE')
        mod = ob.modifiers.new('rig', 'ARMATURE')
        mod.object = rig
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
    traced from the drawing and laid onto the surface it falls on, so it moves with that part."""
    tmp = os.path.join(OUT, '_pass1.png')
    camera('_pass1', pitch=0.0)
    regions = tr.regions(tr.missing_lines(tmp))
    os.remove(tmp)
    from mathutils.geometry import tessellate_polygon
    targets = {}
    for name, (ob, bones, line) in PARTS.items():
        if line == 0 and name not in ('glasses',):
            continue
        me = ob.data
        out_i = [i for i, m in enumerate(me.materials) if m and m.name == 'outline']
        polys = [p.vertices[:] for p in me.polygons if p.material_index not in out_i]
        targets[name] = BVHTree.FromPolygons([v.co.copy() for v in me.vertices], polys)
    per = {}
    for outer, holes in regions:
        cx = sum(p[0] for p in outer) / len(outer)
        cy = sum(p[1] for p in outer) / len(outer)
        hit = None
        for k, (x, y) in enumerate([(cx, cy)] + outer[::max(1, len(outer) // 12)]):
            hs = [(n, t.ray_cast(P(x, y, -400), Vector((0, 1, 0)))) for n, t in targets.items()]
            hs = [(n, h) for n, h in hs if h[0] is not None]
            if hs:
                hit = min(hs, key=lambda nh: nh[1][3])[0]
                break
        if hit is None:
            continue
        per.setdefault(hit, []).append((outer, holes))
    for name, regs in per.items():
        tree = targets[name]
        # lay the shapes out flat in drawing px, split them finely, then drop every point onto the
        # surface (with only outline points the fill would cut chords through a curved surface)
        bm = bmesh.new()
        for outer, holes in regs:
            loops = [outer] + holes
            vs = [bm.verts.new((x, y, 0)) for loop in loops for x, y in loop]
            for tri in tessellate_polygon([[Vector((x, y, 0)) for x, y in loop] for loop in loops]):
                try:
                    bm.faces.new([vs[i] for i in tri])
                except ValueError:
                    pass
        for _ in range(8):
            long_ = [e for e in bm.edges if e.calc_length() > 3.0]
            if not long_:
                break
            bmesh.ops.subdivide_edges(bm, edges=long_, cuts=1, use_grid_fill=False)
            bmesh.ops.triangulate(bm, faces=bm.faces[:])
        last, facing = 0.0, {}
        for v in bm.verts:
            x, y = v.co.x, v.co.y
            h = tree.ray_cast(P(x, y, -400), Vector((0, 1, 0)))
            if h[0] is not None:
                last = h[0].y
                facing[v] = -h[1].y
            v.co = Vector((P(x, y).x, last - 0.8 * S, P(x, y).z))
        # lines on surfaces seen edge-on would smear into streaks from other angles: leave them out
        bad = [f for f in bm.faces if sum(facing.get(v, 0.0) for v in f.verts) / len(f.verts) < 0.3]
        bmesh.ops.delete(bm, geom=bad, context='FACES')
        me = bpy.data.meshes.new(f'lines.{name}')
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(f'lines.{name}', me)
        COL.objects.link(ob)
        me.materials.append(flat('ink'))
        fix_facing(ob)
        part(ob, PARTS[name][1], 0)


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
    skin(RIG)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'doodle.blend'))
    if '--glb' in sys.argv:
        export_glb(os.path.join(OUT, 'doodle.glb'))
    if '--render' in sys.argv:
        camera('front')
        camera('three_quarter', yaw=-35, pitch=-6)
        camera('side', yaw=-90, pitch=-6)
        camera('back', yaw=180, pitch=-6)
