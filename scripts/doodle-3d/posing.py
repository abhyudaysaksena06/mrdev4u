# Posing helpers for the rigged doodle (doodle.blend from build_model.py), for animation scripts:
#
#   import bpy, posing
#   bpy.ops.wm.open_mainfile(filepath='doodle.blend')
#   rig = bpy.data.objects['doodle_rig']
#   posing.aim_arm(rig, 'L', upper=(.7, -.1, .7), fore=(0, -.1, 1), hand=(0, 0, 1), palm=(0, -1, 0))
#   posing.render('wave.png', yaw=-30)
#
# Directions are world space: +X his left, -Y toward the viewer, +Z up.
import bpy
from math import radians
from mathutils import Matrix, Vector

S = 1.75 / (866 - 160)  # metres per drawing px, as in build_model.py


def aim(rig, name, y, z):
    """Pose a bone by direction, the way an animator thinks: its length along world direction y,
    its Z axis (forward / the palm, for arm and hand bones) toward z. The joint limits still apply."""
    pb = rig.pose.bones[name]
    Y = Vector(y).normalized()
    X = Y.cross(Vector(z)).normalized()
    Z = X.cross(Y)
    m = Matrix.Identity(4)
    for i in range(3):
        m[i][0], m[i][1], m[i][2] = X[i], Y[i], Z[i]
    m.translation = pb.matrix.translation
    pb.matrix = m
    bpy.context.view_layer.update()


def aim_arm(rig, side, upper, fore, hand, palm):
    """Aim a whole arm: upper arm, forearm and hand directions plus where the palm faces. The elbow
    hinges in the plane of the two arm bones, as a real elbow does; the hand's turn relative to the
    forearm is taken up by the forearm (twist bone), not wrung at the wrist."""
    u, f = Vector(upper).normalized(), Vector(fore).normalized()
    bend = f - u * f.dot(u)
    zu = bend.normalized() if bend.length > 0.05 else Vector(palm)
    aim(rig, f'upper_arm.{side}', u, zu)
    xf = u.cross(zu).normalized()  # the elbow's hinge axis, shared by both bones
    zf = xf.cross(f) if bend.length > 0.05 else Vector(palm)
    aim(rig, f'forearm.{side}', f, zf)
    aim(rig, f'hand.{side}', hand, palm)


def curl(rig, side, fingers, k, spread=0.0):
    """Curl fingers (0 = straight, 1 = a fist) the way a hand closes: knuckle, then the two joints."""
    for f in fingers:
        for j, amt in zip((1, 2, 3), (75, 95, 65)):
            pb = rig.pose.bones[f'f_{f}.{j:02d}.{side}']
            pb.rotation_euler = (radians(amt * k), 0, radians(spread if j == 1 else 0))
    bpy.context.view_layer.update()


def reset(rig):
    for pb in rig.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = (0, 0, 0)
        pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()


def render(path, yaw=0.0, pitch=-4.0, centre_px=(388, 512), scale_px=1024, res=(776, 1024)):
    """Orthographic render like build_model.camera: yaw turns round him (+ shows his left side)."""
    sc = bpy.context.scene
    cam = sc.camera
    target = Vector(((centre_px[0] - 386) * S, 0, (866 - centre_px[1]) * S))
    rot = Matrix.Rotation(radians(yaw), 4, 'Z') @ Matrix.Rotation(radians(pitch), 4, 'X')
    cam.location = target + rot @ Vector((0, -20, 0))
    cam.rotation_euler = (rot @ Matrix.Rotation(radians(90), 4, 'X')).to_euler()
    cam.data.ortho_scale = scale_px * S
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


# ---------------------------------------------------------------- forward kinematics
def frame_from(y, z):
    """Rotation whose Y axis is y and whose Z axis leans toward z."""
    Y = Vector(y).normalized()
    X = Y.cross(Vector(z)).normalized()
    Z = X.cross(Y)
    m = Matrix.Identity(3)
    for i in range(3):
        m[i][0], m[i][1], m[i][2] = X[i], Y[i], Z[i]
    return m


def eul(x=0.0, y=0.0, z=0.0):
    from mathutils import Euler
    return Euler((radians(x), radians(y), radians(z))).to_quaternion()


def fk_arm(rig, side, u, hint, elbow, pron=0.0, flex=0.0, dev=0.0, clav=0.0):
    """Pose an arm by joint rotations, so the rig's joint limits hold: the upper arm along world
    direction u (as if the chest were at rest; chest rotations carry the arm), its elbow bending
    toward `hint`; elbow flexion, hand pronation / flexion / deviation and clavicle lift in degrees.
    The clavicle's share of the lift is taken back out of the upper arm, so u is where it points."""
    pb, bn = rig.pose.bones, rig.data.bones
    for n in (f'shoulder.{side}', f'upper_arm.{side}', f'forearm.{side}', f'hand.{side}'):
        pb[n].rotation_mode = 'QUATERNION'
    S_REST = bn[f'shoulder.{side}'].matrix_local.to_3x3()
    U_REST = bn[f'upper_arm.{side}'].matrix_local.to_3x3()
    q_s = eul(0, 0, clav)
    Rs = S_REST @ q_s.to_matrix() @ S_REST.inverted()
    pb[f'shoulder.{side}'].rotation_quaternion = q_s
    pb[f'upper_arm.{side}'].rotation_quaternion = (U_REST.inverted() @ Rs.inverted() @ frame_from(u, hint)).to_quaternion()
    pb[f'forearm.{side}'].rotation_quaternion = eul(elbow)
    pb[f'hand.{side}'].rotation_quaternion = eul(flex, pron, dev)


def rot(rig, name, x=0.0, y=0.0, z=0.0):
    """Local rotation in degrees. Spine, neck, head, hips: X bends forward, Y turns (to his left
    for +), Z tilts (+ toward his right)."""
    pb = rig.pose.bones[name]
    pb.rotation_mode = 'QUATERNION'
    pb.rotation_quaternion = eul(x, y, z)


def curl_all(rig, side, k):
    for f in ('index', 'middle', 'ring', 'pinky'):
        for j, amt in zip((1, 2, 3), (75, 95, 65)):
            pb = rig.pose.bones[f'f_{f}.{j:02d}.{side}']
            pb.rotation_mode = 'QUATERNION'
            pb.rotation_quaternion = eul(amt * k)


# Stress poses for checking how the model deforms (check.py renders them): each is a function of
# the rig. Directions are world space: +X his left, -Y toward the viewer, +Z up.
def _sym(rig, u, hint, elbow, **kw):
    fk_arm(rig, 'L', u, hint, elbow, **kw)
    fk_arm(rig, 'R', (-u[0], u[1], u[2]), (-hint[0], hint[1], hint[2]), elbow, **kw)


STRESS = {
    'arms_up': lambda r: _sym(r, (0.38, -0.08, 0.92), (-0.9, 0.1, 0.4), 12, clav=24),
    't_pose': lambda r: _sym(r, (1, 0, 0.04), (0, -1, 0), 4, clav=8),
    'reach_forward': lambda r: (_sym(r, (0.16, -1, 0.02), (0, 0, 1), 8, clav=6), rot(r, 'spine', 6)),
    'arms_bent': lambda r: _sym(r, (0.3, -0.05, -0.95), (0, -1, 0), 135),
    'hug_cross': lambda r: (fk_arm(r, 'R', (0.45, -0.85, -0.25), (1, 0, 0.3), 115),
                            fk_arm(r, 'L', (0.2, -0.3, -0.93), (0, -1, 0), 20)),
    'crouch': lambda r: (setattr(r.pose.bones['hips'], 'location', (0, -0.16, 0.04)), rot(r, 'hips', 0),
                         rot(r, 'spine', 14), rot(r, 'chest', 8), rot(r, 'head', -14)),
    'twist_bend': lambda r: (rot(r, 'spine', 0, 16, 6), rot(r, 'chest', 0, 16, 8), rot(r, 'neck', 0, 20, -6),
                             rot(r, 'head', 0, 22, -8)),
}
