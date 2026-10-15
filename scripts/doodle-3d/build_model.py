# Builds the doodle character (scripts/doodle-trace/reference.png) as a rigged 3D toon model.
#
#   pip install bpy==5.2.2          # Blender as a Python module, runs headless
#   python3 build_model.py <out_dir> [--render] [--glb]
#
# Writes <out_dir>/doodle.blend, plus front/three-quarter/side/back renders with --render and
# <out_dir>/doodle.glb with --glb.
#
# Everything is measured in pixels of the reference drawing (x right, y down, d = depth, negative
# toward the viewer) and converted to metres by P(): the figure stands 1.75 m tall on the origin,
# facing -Y, the Blender convention (so the character's left, ".L", is +X).
#
# The look matches the drawing: flat unlit colours and an ink outline. The outline is an "inverted
# hull" (a slightly larger copy of each mesh, faces flipped, drawn in ink only where it shows behind
# the surface), so it is real geometry that deforms with the rig and exports to three.js.
import bpy, bmesh, math, sys, os
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

    def drop(x, y):
        o = P(x, y, -400)
        hits = [t.ray_cast(o, Vector((0, 1, 0))) for t in trees]
        hits = [h for h in hits if h[0] is not None]
        if not hits:
            return P(x, y, 0), Vector((0, -1, 0))
        h = min(hits, key=lambda h: h[3])
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
    ear = ellipsoid(f'ear.{"L" if side > 0 else "R"}', (CX + side * 54, 281, 4), (8, 17, 10), ['skin'],
                    rot=(0, 0, side * -18))
    smooth(ear, 1)
    part(ear, ['head'])

# Hair: a cluster of curls (spheres), fused into one surface by a voxel remesh so the outline
# scallops like the drawing without lines between the curls.
HAIR = [
    # cap over the skull and the back of the head: (x, y, d, half width, half height, half depth)
    (386, 214, 2, 56, 46, 66), (386, 252, 36, 52, 34, 40),
    # big curls on the outline
    (342, 192, -4, 24), (368, 180, -8, 22), (396, 178, -8, 23), (424, 186, -6, 22), (442, 206, 0, 17),
    (443, 230, 4, 15), (440, 248, 8, 12), (328, 212, 0, 19), (325, 236, 4, 15), (330, 250, 8, 11),
    # fringe: a lock on his right, a parting, the rest swept to his left
    (338, 228, -40, 14), (345, 238, -48, 11), (380, 220, -56, 15), (402, 221, -58, 15), (424, 225, -52, 15),
    (438, 232, -42, 12), (360, 202, -50, 17), (388, 198, -56, 18), (414, 202, -54, 17),
]
curls = []
for h in HAIR:
    x, y, d = h[:3]
    r = h[3:] if len(h) == 6 else (h[3], h[3], h[3])
    c = ellipsoid('curl', (x, y, d), r, ['hair'], n=20)
    curls.append(c)
bpy.ops.object.select_all(action='DESELECT')
for c in curls:
    c.select_set(True)
bpy.context.view_layer.objects.active = curls[0]
bpy.ops.object.join()
hair = bpy.context.view_layer.objects.active
hair.name = 'hair'
rm = hair.modifiers.new('fuse', 'REMESH')
rm.mode = 'VOXEL'
rm.voxel_size = 1.8 * S
sm = hair.modifiers.new('soften', 'SMOOTH')
sm.factor, sm.iterations = 1.0, 30
dc = hair.modifiers.new('lighter', 'DECIMATE')
dc.ratio = 0.3
apply_mods(hair)
for p in hair.data.polygons:
    p.use_smooth = True
part(hair, ['head'])
part(decal('hairlines', [stroke([(372, 206), (377, 214), (379, 224)], 3.4, 2.2), stroke([(398, 210), (401, 218), (399, 226)], 3.4, 2.2),
                         stroke([(428, 212), (432, 220), (431, 230)], 3.4, 2.2)], [hair], 'ink', lift=0.8), ['head'], 0)

# Face details, drawn in the drawing's own coordinates and dropped onto the face.
face_t = [head]
part(decal('brows', [stroke([(345, 249.5), (352, 246), (360, 244.6), (368, 245.2), (375, 247.5)], 7.2, 8.0),
                     stroke([(400, 247.5), (407, 245.2), (415, 244.6), (423, 246), (430, 249.5)], 8.0, 7.2)],
           face_t + [hair], 'ink', lift=1.2), ['head'], 0)
part(decal('eyes', [oval(361.5, 269.8, 4.7, 6.7), oval(411.5, 269.8, 4.7, 6.7)], face_t, 'ink', lift=0.8), ['head'], 0)
part(decal('nose', [stroke([(380, 288.5), (386.5, 291.5), (393, 288.5)], 3.6)], face_t, 'ink', lift=0.8), ['head'], 0)
MOUTH = [(365.5, 305.2), (380, 303.5), (395, 302.2), (409.5, 301.2)]
MOUTH_LOW = [(409.5, 301.2), (405, 308), (397, 313.5), (387, 315.6), (377, 314), (370, 310), (365.5, 305.2)]
part(decal('mouth_in', [MOUTH + MOUTH_LOW[1:-1]], face_t, 'skin', lift=1.0), ['head'], 0)
part(decal('mouth', [stroke(MOUTH, 4.4), stroke(MOUTH_LOW, 4.0)], face_t, 'ink', lift=1.6, ), ['head'], 0)
for side, cx in ((-1, 324.5), (1, 447.5)):
    part(decal(f'earline.{"L" if side > 0 else "R"}',
               [stroke([(cx + side * 1, 274), (cx - side * 3, 277), (cx - side * 3.5, 285), (cx + side * 0.5, 289)], 2.6)],
               [PARTS[f'ear.{"L" if side > 0 else "R"}'][0]], 'ink', lift=0.8), ['head'], 0)

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
paint(neck, lambda p, f: 'shade' if p[1] < 352 or p[0] > CX + 2 else None)
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
    x, y = CX + 31 * cos(t), 373 - 10 * sin(t)
    collar_pts.append((x, y, surf(TEE, x, y, sin(t) < 0) + (-3 if sin(t) < 0 else 3)))
collar = tube('collar', collar_pts, [4.0] * 29, ['tee'], ref=Vector((0, 0, 1)), n=10, caps=(None, None))
part(collar, ['chest', 'neck'])

# Hoodie body: open at the front where the tee shows; the gap keeps its width all the way down.
GAP = 26.5
HOOD_BODY = [(350, 44, 36, 6), (362, 62, 44, 4), (380, 76, 51, 2), (400, 80, 54, 0), (450, 81, 55, 0),
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
for y, w, d in ((576, 80.5, 56), (595, 79.5, 55.5)):
    phi = asin(GAP / w)
    rings.append(hring(y, w, d, 0, n=33, a0=-pi / 2 + phi, a1=3 * pi / 2 - phi, closed=False))
hem = loft('hem', rings, ['hoodie'], closed=False)
smooth(hem, 1)
solidify(hem, 4.0, 'hoodin')
part(hem, ['hips'])

# Hood: a thick rim around the neck, dark inside, with the lime piping on its outer edge.
HOOD = [(354, 404, -50), (344, 384, -44), (333, 356, -30), (329, 336, -12), (334, 322, 10), (354, 314, 30),
        (386, 312, 38)]
hood_path = HOOD + mirror_x(HOOD[::-1])[1:]
neck_axis = P(CX, 0, 10)


def outward(i, c):
    r = Vector((c.x - neck_axis.x, c.y - neck_axis.y, 0))
    return r.normalized() if r.length > 1e-6 else Vector((0, 1, 0))


hood = tube('hood', hood_path, [(7.5, 9)] * len(hood_path), ['hoodie'], ref=outward, n=16, caps=(0.5, 0.5))
smooth(hood)
ang = tube_angle(hood, outward)
paint(hood, lambda p, f: 'lime' if (-25 < ang(p)[0] < 30 and p[1] < 362) else ('navy' if abs(ang(p)[0]) > 120 else None))
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
ARM = [(346, 352, -2, 12), (318, 366, 0, 24), (300, 384, 1, 33), (284, 412, 2, 33), (270, 450, 3, 31),
       (262, 490, 3, 30), (258, 530, 3, 29), (259, 560, 2, 27), (261, 574, 2, 23)]


def arm(side):
    nm = 'L' if side > 0 else 'R'
    pts = [(CX + side * (CX - x), y, d) for x, y, d, r in ARM]
    out = Vector((side, 0, 0))
    sl = tube(f'sleeve.{nm}', pts, [r for *_, r in ARM], ['hoodie'], ref=out, n=24, caps=(0.6, 0.3))
    smooth(sl)
    a = tube_angle(sl, out)

    def stripe(p, f):
        g, s_ = a(p)
        # angle 0 is straight out, +/-90 is front/back (v = t x u)
        front = -g if side < 0 else g
        return 'lime' if (s_ > 0.7 and -8 < front < 34) else None
    paint(sl, stripe)
    part(sl, [f'shoulder.{nm}', f'upper_arm.{nm}', f'forearm.{nm}', 'chest'])

    cx = CX + side * (CX - 260)
    cuff = loft(f'cuff.{nm}', [hring(y, 21.5, 20, 2, x=cx) for y in (576, 586, 595)], ['hoodie'],
                caps=(None, P(cx, 597, 2)))
    smooth(cuff)
    part(cuff, [f'forearm.{nm}'])

    hand(side, nm, cx)


def hand(side, nm, cx, turn=30):
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
                   [(17, 8), (21, 9), (22, 9.5), (21, 9)], ['skin'], ref=Xw, n=16, e=2.6, caps=(0.5, 0.4))]
    # little finger to index: knuckle x, length, spread
    for fx, fl, sp in ((-15, 25, -4), (-5, 31, -1.5), (5, 32, 1), (15, 28, 3)):
        k = H(fx, -2, -30)
        mid = H(fx + sp * 0.5, -3, -30 - fl * 0.55)
        tip = H(fx + sp, -7, -30 - fl)
        pieces.append(tube('finger', [k, mid, tip], [5.4, 5.0, 4.6], ['skin'], ref=Xw, n=12, caps=(0.5, 0.95)))
    pieces.append(tube('thumb', [H(16, -6, -8), H(24, -11, -22), H(27, -13, -36)], [6.6, 5.8, 5.2], ['skin'],
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

# ================================================================ LEGS
pelvis = loft('pelvis', [hring(y, w, d, 0) for y, w, d in
                         ((592, 78, 52), (606, 79, 50), (620, 77, 42), (634, 68, 35), (646, 50, 30))],
              ['pants'], caps=(P(CX, 586, 0), P(CX, 650, 0)))
smooth(pelvis)
legs = [pelvis]
LEG = [(46, 630, 33), (46, 700, 31), (50, 760, 30), (53, 810, 29), (54, 829, 28)]
for side in (-1, 1):
    leg = loft('leg', [hring(y, r, r * (1.06 if y < 650 else 0.95), 0, x=CX + side * o, n=20) for o, y, r in LEG], ['pants'],
               caps=(P(CX + side * 46, 624, 0), P(CX + side * 54, 832, 0)))
    smooth(leg)
    legs.append(leg)
# one pants surface, rounded where the legs meet the hips so no crease line shows
bpy.ops.object.select_all(action='DESELECT')
for o in legs:
    o.select_set(True)
bpy.context.view_layer.objects.active = pelvis
bpy.ops.object.join()
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
    yaw = side * 50
    ob = ellipsoid(f'shoe.{nm}', (CX, FLOOR, 0), (30, 20, 66), ['shoe'])
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
    ob.location = P(CX + side * 81, 846, -22)
    apply_transform(ob)
    smooth(ob, 1)
    part(ob, [f'foot.{nm}'])


shoe(-1)
shoe(1)

# ground shadow (not part of the character)
sh = ellipsoid('shadow', (CX + 3, 866, -10), (163, 0.5, 150), ['shadow'])

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


def camera(name, yaw=0.0, pitch=-6.0, res=(776, 1024), centre=(388, 512), scale_px=1024):
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


if __name__ == '__main__':
    finish_outlines()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'doodle.blend'))
    if '--render' in sys.argv:
        camera('front')
        if '--all' in sys.argv:
            camera('three_quarter', yaw=-35, centre=(388, 512))
            camera('side', yaw=-90)
            camera('back', yaw=180)
