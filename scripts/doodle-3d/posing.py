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
