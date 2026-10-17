# "Hi!" wave for the rigged doodle (doodle.blend from build_model.py), keyed frame by frame.
#
#   python3 anim_wave.py <doodle.blend> <out_dir> [--render] [--yaw=-25]
#
# Writes <out_dir>/doodle_wave.blend (the animation baked as keys on the rig, 30 fps) and, with
# --render, the frames to <out_dir>/wave_<yaw>/ for ffmpeg.
#
# The motion follows how a person waves:
#   0.00-0.35  rest, breathing; a small dip of the knees (anticipation)
#   0.35-0.95  the arm lifts out to the side: the shoulder leads, the elbow folds as it rises so the
#              hand travels close, the clavicle lifts, weight shifts onto the right leg (contrapposto),
#              the hand trails the forearm and the fingers open and fan out a beat late
#   0.95-2.40  three waves: the forearm swings about the elbow (windscreen-wiper), the upper arm rocks
#              a little against it, the hand lags behind the forearm and flicks at each turn (a
#              damped spring, the way a loose wrist moves), the fingers ripple; a nod on "hi" and the
#              head tilts toward the hand
#   2.40-3.10  the arm drops, slightly faster than it rose, swings a touch past and settles; fingers
#              relax; weight comes back to both feet
#   3.10-3.70  settle and hold (loops cleanly back to the start)
# Arm, elbow and hand are posed as joint rotations (forward kinematics), so every pose stays inside
# the rig's human joint limits. Feet stay planted by the leg IK.
import bpy, sys, os
from math import radians, degrees, sin, cos, pi, atan2
from mathutils import Matrix, Quaternion, Vector, Euler

args = [a for a in sys.argv[1:] if not a.startswith('--')]
BLEND, OUT = os.path.abspath(args[0]), os.path.abspath(args[1])
YAW = float(next((a.split('=')[1] for a in sys.argv if a.startswith('--yaw=')), '0'))
os.makedirs(OUT, exist_ok=True)

FPS, DUR = 30, 3.7
N = int(round(DUR * FPS))

bpy.ops.wm.open_mainfile(filepath=BLEND)
SC = bpy.context.scene
rig = bpy.data.objects['doodle_rig']
PB, BN = rig.pose.bones, rig.data.bones
S = 1.75 / (866 - 160)  # metres per drawing px

for pb in PB:
    pb.rotation_mode = 'QUATERNION'


# ---------------------------------------------------------------- curves
def curve(t, ks):
    """Smooth curve through keys [(time, value)]: cubic Hermite, flat at the ends and at peaks
    (auto-clamped, like an animator's F-curve)."""
    if t <= ks[0][0]:
        return ks[0][1]
    if t >= ks[-1][0]:
        return ks[-1][1]
    i = max(j for j in range(len(ks) - 1) if ks[j][0] <= t)
    (t0, v0), (t1, v1) = ks[i], ks[i + 1]

    def tan(j):
        if j == 0 or j == len(ks) - 1:
            return 0.0
        a, b, c = ks[j - 1][1], ks[j][1], ks[j + 1][1]
        if (b - a) * (c - b) <= 0:
            return 0.0
        return (c - a) / (ks[j + 1][0] - ks[j - 1][0])
    h = t1 - t0
    s = (t - t0) / h
    m0, m1 = tan(i) * h, tan(i + 1) * h
    return ((2 * s ** 3 - 3 * s ** 2 + 1) * v0 + (s ** 3 - 2 * s ** 2 + s) * m0
            + (-2 * s ** 3 + 3 * s ** 2) * v1 + (s ** 3 - s ** 2) * m1)


def spring(target, f=3.0, zeta=0.45):
    """Follow a target signal like a mass on a spring: lags, overshoots, settles."""
    w = 2 * pi * f
    x, v, out = target[0], 0.0, []
    sub = 8
    for k in range(len(target)):
        for _ in range(sub):
            dt = 1 / (FPS * sub)
            a = w * w * (target[k] - x) - 2 * zeta * w * v
            v += a * dt
            x += v * dt
        out.append(x)
    return out


T = [k / FPS for k in range(N + 1)]

RAISE = [(0, 0), (0.36, 0), (0.84, 1.05), (1.0, 1.0), (2.4, 1.0), (2.92, -0.03), (3.12, 0.008), (3.3, 0)]
ELBOW = [(0, 0), (0.4, 0), (0.78, 1.0), (2.42, 1.0), (2.86, 0.06), (3.05, 0)]
WAVE_ENV = [(0, 0), (0.92, 0), (1.08, 1.0), (2.12, 1.0), (2.4, 0)]
WAVE_F, WAVE_T0 = 2.25, 0.96          # waves per second, start of the first swing
OPEN = [(0, 0), (0.5, 0), (0.9, 1.0), (2.45, 1.0), (2.9, 0)]     # fingers open and fan
SHIFT = [(0, 0), (0.42, 0), (1.0, 1.0), (2.5, 1.0), (3.2, 0)]    # weight onto the right leg
DIP = [(0, 0), (0.2, 0), (0.36, -1.0), (0.62, 0.35), (0.85, 0)]  # anticipation dip, push up
NOD = [(0, 0), (0.98, 0), (1.12, 1.0), (1.3, -0.25), (1.46, 0.3), (1.62, 0)]

r = [curve(t, RAISE) for t in T]
el = [curve(t, ELBOW) for t in T]
env = [curve(t, WAVE_ENV) for t in T]
wave = [env[k] * sin(2 * pi * WAVE_F * max(0.0, T[k] - WAVE_T0)) for k in range(N + 1)]
opn = spring([curve(t, OPEN) for t in T], f=2.2, zeta=0.6)
shift = [curve(t, SHIFT) for t in T]
dip = [curve(t, DIP) for t in T]
nod = spring([curve(t, NOD) for t in T], f=3.0, zeta=0.5)


# ---------------------------------------------------------------- the waving arm (his left)
def rest_rot(name):
    return BN[name].matrix_local.to_3x3()


def frame_from(y, z):
    Y = Vector(y).normalized()
    X = Y.cross(Vector(z)).normalized()
    Z = X.cross(Y)
    m = Matrix.Identity(3)
    for i in range(3):
        m[i][0], m[i][1], m[i][2] = X[i], Y[i], Z[i]
    return m


SIDE = 'L'
U_REST, F_REST, H_REST = rest_rot(f'upper_arm.{SIDE}'), rest_rot(f'forearm.{SIDE}'), rest_rot(f'hand.{SIDE}')
S_REST = rest_rot(f'shoulder.{SIDE}')
# raised: upper arm out to the side, a little forward and up; it bends toward his head
U_UP = frame_from((0.80, -0.15, 0.50), (-0.5, 0.15, 0.85))
Q_U = (U_REST.inverted() @ U_UP).to_quaternion()
E_UP = radians(45)            # elbow flexion when raised: forearm upright beside the head
E_WAVE = radians(17)          # half the swing


def forearm_world(q_u, e):
    """Forearm rotation (armature space, shoulder at rest) for an upper-arm basis and elbow angle."""
    up = U_REST @ q_u.to_matrix()
    return up @ (U_REST.inverted() @ F_REST) @ Matrix.Rotation(e, 3, 'X')


def hand_world(fw, pron, flex=0.0, dev=0.0):
    return fw @ (F_REST.inverted() @ H_REST) @ Euler((flex, pron, dev)).to_matrix()


# the hand's turn (pronation) that shows the palm to the viewer when raised
FW_UP = forearm_world(Q_U, E_UP)
PRON = max((radians(a) for a in range(-85, 86)),
           key=lambda p: hand_world(FW_UP, p).col[2].dot(Vector((0, -1, 0))))
# which way a + deviation turns the hand in the frontal plane (to apply the drag the right way)
ang = lambda m: atan2(m.col[1].x, m.col[1].z)
DEV_SIGN = 1 if ang(hand_world(FW_UP, PRON, dev=radians(5))) > ang(hand_world(FW_UP, PRON)) else -1


def slerp_ext(q, t):
    """Identity -> q by t, allowing t a little past 0..1 (overshoot)."""
    axis, a = q.to_axis_angle()
    return Quaternion(axis, a * t)


# per frame: upper arm, elbow, forearm angle in the frontal plane
arm = []
for k in range(N + 1):
    rock = Quaternion(Vector((0, 1, 0)), radians(-4) * wave[k])       # upper arm rocks against the swing
    q_u = slerp_ext(Q_U, r[k])
    q_u = (U_REST.inverted() @ rock.to_matrix() @ U_REST @ q_u.to_matrix()).to_quaternion() if env[k] else q_u
    e = E_UP * el[k] + E_WAVE * wave[k]
    arm.append((q_u, e, ang(forearm_world(q_u, e))))
# the hand trails the forearm: its angle in the frontal plane follows the forearm's on a spring
phi = [a[2] for a in arm]
for k in range(1, len(phi)):  # unwrap
    while phi[k] - phi[k - 1] > pi:
        phi[k] -= 2 * pi
    while phi[k] - phi[k - 1] < -pi:
        phi[k] += 2 * pi
hand_phi = spring(phi, f=3.4, zeta=0.32)
drag = [max(-radians(24), min(radians(30), DEV_SIGN * (hand_phi[k] - phi[k]))) for k in range(N + 1)]
# fingers ripple behind the wrist
ripple = spring([d for d in drag], f=4.0, zeta=0.4)


# ---------------------------------------------------------------- pose and key every frame
def setq(name, q):
    PB[name].rotation_quaternion = q


def eul(x=0.0, y=0.0, z=0.0):
    return Euler((radians(x), radians(y), radians(z))).to_quaternion()


FINGERS = {'index': 6, 'middle': 2, 'ring': -3, 'pinky': -9}
KEYED = set()

for k in range(N + 1):
    t = T[k]
    for pb in PB:
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
    breathe = sin(2 * pi * t / 3.3)
    # body: hips drop a little, shift onto the right leg and tilt (right hip up); chest counters
    # (vertical bones: local X = his left, Y = up, Z = toward the viewer)
    PB['hips'].location = (-0.016 * shift[k], -0.006 * shift[k] + 0.007 * dip[k] - 0.004, 0.0)
    setq('hips', eul(0, 0, -2.6 * shift[k]))
    setq('spine', eul(0.6 * breathe, 0, 1.2 * shift[k]))
    setq('chest', eul(0.8 * breathe - 1.2 * dip[k], 0, 2.6 * shift[k] + 0.8 * wave[k]))
    setq('neck', eul(2.0 * nod[k], 0, -2.0 * shift[k]))
    setq('head', eul(5.5 * nod[k] - 1.0 * dip[k], 5.0 * shift[k], -6.5 * shift[k] - 0.8 * wave[k]))
    # waving arm
    q_u, e, _ = arm[k]
    # the clavicle carries part of the lift (shoulder rhythm, about 1 : 3 of the arm's), so the bend
    # is shared between the shoulder girdle and the joint, as on a person; the arm's own rotation
    # gives that part back, keeping the hand where it was aimed
    q_s = eul(0, 0, 18 * max(0.0, r[k]))
    setq(f'shoulder.{SIDE}', q_s)
    Rs = S_REST @ q_s.to_matrix() @ S_REST.inverted()
    setq(f'upper_arm.{SIDE}', (U_REST.inverted() @ Rs.inverted() @ U_REST @ q_u.to_matrix()).to_quaternion())
    setq(f'forearm.{SIDE}', eul(degrees(e)))
    lift = max(0.0, min(1.0, r[k]))
    setq(f'hand.{SIDE}', Euler((radians(-6) * lift, PRON * lift, drag[k] * lift)).to_quaternion())
    for f, sp in FINGERS.items():
        o = opn[k]
        w = ripple[k] * 0.25 * (1 + 0.3 * list(FINGERS).index(f))
        setq(f'f_{f}.01.{SIDE}', eul(-6 * o + degrees(w) * 0.4, 0, sp * o))
        setq(f'f_{f}.02.{SIDE}', eul(-3 * o + 4 * (1 - o) + degrees(abs(w)) * 0.2))
        setq(f'f_{f}.03.{SIDE}', eul(2 * (1 - o)))
    setq(f'f_thumb.01.{SIDE}', eul(-8 * opn[k], 0, 14 * opn[k]))
    # resting arm: hangs, sways a little with the body, fingers soft
    setq('upper_arm.R', eul(0, 0, 1.5 * shift[k] + 0.6 * breathe))
    setq('forearm.R', eul(6 + 2 * shift[k]))
    for f in FINGERS:
        setq(f'f_{f}.02.R', eul(8))
    # key it
    for pb in PB:
        if pb.rotation_quaternion != Quaternion((1, 0, 0, 0)) or pb.location.length > 0 or pb.name in KEYED:
            pb.keyframe_insert('rotation_quaternion', frame=k + 1)
            pb.keyframe_insert('location', frame=k + 1)
            KEYED.add(pb.name)

if rig.animation_data and rig.animation_data.action:
    rig.animation_data.action.name = 'wave_hi'
    for fc in rig.animation_data.action.fcurves if hasattr(rig.animation_data.action, 'fcurves') else []:
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
SC.render.fps = FPS
SC.frame_start, SC.frame_end = 1, N + 1
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'doodle_wave.blend'))
print('frames', N + 1, 'pronation', round(degrees(PRON)), 'dev sign', DEV_SIGN,
      'max drag', round(degrees(max(abs(d) for d in drag)), 1))

if '--render' in sys.argv:
    cam = SC.camera
    target = Vector(((388 - 386) * S, 0, (866 - 512) * S))
    rot = Matrix.Rotation(radians(YAW), 4, 'Z') @ Matrix.Rotation(radians(-3), 4, 'X')
    cam.location = target + rot @ Vector((0, -20, 0))
    cam.rotation_euler = (rot @ Matrix.Rotation(radians(90), 4, 'X')).to_euler()
    cam.data.ortho_scale = 1024 * S
    SC.render.resolution_x, SC.render.resolution_y = 776, 1024
    SC.cycles.samples = 16
    SC.render.image_settings.file_format = 'PNG'
    SC.render.filepath = os.path.join(OUT, f'wave_{int(YAW)}', '')
    bpy.ops.render.render(animation=True)
