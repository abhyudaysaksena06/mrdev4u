# Review harness for the 3D doodle: builds the model, bakes the wave, renders the poses that
# matter and puts them on review sheets, with numbers for how closely the standing pose matches
# the drawing. Use it before and after every change to the model or rig.
#
#   python3 check.py <out_dir>            # full: build, bake, render, sheets, metrics
#   python3 check.py <out_dir> --no-build # reuse <out_dir>/doodle.blend and doodle_wave.blend
#
# Writes into <out_dir>:
#   metrics.json         silhouette IoU with the drawing (higher is better, 1 = identical) and
#                        ink-line distance in px (lower is better) for the standing front view
#   sheet_match.png      drawing | model | overlay, and an ink overlay (blue drawing, red model)
#   sheet_shoulder.png   the wave at the moments the arm is up, front and three-quarter, zoomed
#                        on the shoulder and underarm
#   sheet_stress.png     stress poses (arms up, T, reach, bent, across, crouch, twist), front and
#                        three-quarter: where skinning, joints and cloth show their faults
import json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, '..', 'doodle-trace', 'reference.png')
BG = (230, 236, 236)
WAVE_FRAMES = [(55, 0), (61, 0), (72, 0), (61, -30), (72, -30), (88, -30)]   # PRE=30: arm rising, up, waving
STRESS_VIEWS = [0, -35]


def run(*cmd):
    r = subprocess.run([sys.executable, *cmd], capture_output=True, text=True)
    if r.returncode:
        sys.stderr.write(r.stdout[-3000:] + r.stderr[-3000:])
        raise SystemExit(f'failed: {cmd[0]}')


def flat_bg(path):
    im = Image.open(path).convert('RGBA')
    bg = Image.new('RGBA', im.size, BG + (255,))
    bg.alpha_composite(im)
    return bg.convert('RGB'), np.array(im)[..., 3] > 127


# ---------------------------------------------------------------- inside Blender
def render_stage(out):
    import bpy
    from math import radians
    from mathutils import Matrix, Vector
    sys.path.insert(0, HERE)
    import posing
    S = posing.S

    def cam_render(path, yaw, pitch=-4.0):
        sc = bpy.context.scene
        cam = sc.camera
        rot = Matrix.Rotation(radians(yaw), 4, 'Z') @ Matrix.Rotation(radians(pitch), 4, 'X')
        cam.location = Vector((2 * S, 0, 354 * S)) + rot @ Vector((0, -20, 0))
        cam.rotation_euler = (rot @ Matrix.Rotation(radians(90), 4, 'X')).to_euler()
        cam.data.ortho_scale = 1024 * S
        sc.render.resolution_x, sc.render.resolution_y = 776, 1024
        sc.cycles.samples = 12
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)

    wave = os.path.join(out, 'doodle_wave.blend')
    if os.path.exists(wave):
        bpy.ops.wm.open_mainfile(filepath=wave)
        for f, yaw in WAVE_FRAMES:
            bpy.context.scene.frame_set(f)
            cam_render(os.path.join(out, 'chk', f'wave_{f}_{yaw}.png'), yaw)
    for name, pose in posing.STRESS.items():
        bpy.ops.wm.open_mainfile(filepath=os.path.join(out, 'doodle.blend'))
        rig = bpy.data.objects['doodle_rig']
        posing.reset(rig)
        pose(rig)
        bpy.context.view_layer.update()
        for yaw in STRESS_VIEWS:
            cam_render(os.path.join(out, 'chk', f'stress_{name}_{yaw}.png'), yaw)


# ---------------------------------------------------------------- sheets and numbers
def metrics(out):
    sys.path.insert(0, HERE)
    import trace as tr
    from scipy import ndimage as ndi
    ref = tr.rgb()
    # the drawing's figure: everything that is not the paper colour, holes filled, shadow cut
    fg_ref = np.sqrt(((ref - np.array(BG)) ** 2).sum(-1)) > 28
    fg_ref = ndi.binary_fill_holes(ndi.binary_closing(fg_ref, tr.disk(2)))
    fg_ref = ndi.binary_opening(fg_ref, tr.disk(2))
    img, alpha = flat_bg(os.path.join(out, 'front.png'))
    model = np.array(img).astype(int)
    shadow = np.zeros_like(alpha)
    shadow[852:] = True
    ys, xs = np.nonzero(alpha & ~shadow)
    figure = alpha.copy()
    lab, n = ndi.label(fg_ref & ~shadow)
    sizes = ndi.sum(fg_ref, lab, range(1, n + 1))
    fg_ref = lab == (1 + int(np.argmax(sizes)))
    figure &= ~shadow
    inter, union = (figure & fg_ref).sum(), (figure | fg_ref).sum()
    ink_ref, ink_mod = tr.ink(ref), tr.ink(model)
    ink_ref[852:] = ink_mod[852:] = False
    d_mod = ndi.distance_transform_edt(~ink_mod)
    d_ref = ndi.distance_transform_edt(~ink_ref)
    res = {
        'silhouette_iou': round(float(inter / union), 4),
        'ink_drawing_to_model_px': round(float(d_mod[ink_ref].mean()), 2),
        'ink_model_to_drawing_px': round(float(d_ref[ink_mod].mean()), 2),
        'ink_drawing_lines_matched_within_3px': round(float((d_mod[ink_ref] <= 3).mean()), 4),
    }
    # region scores: where the mismatch is
    for name, (y0, y1) in {'head': (150, 345), 'torso_arms': (345, 600), 'legs_feet': (600, 852)}.items():
        a, b = figure[y0:y1], fg_ref[y0:y1]
        res[f'iou_{name}'] = round(float((a & b).sum() / max(1, (a | b).sum())), 4)
        r = ink_ref[y0:y1]
        res[f'ink_matched_{name}'] = round(float((d_mod[y0:y1][r] <= 3).mean()), 4)
    # ink overlay image
    ov = np.full(ref.shape, 255, np.uint8)
    ov[ink_ref] = (60, 120, 255)
    ov[ink_mod] = (255, 70, 70)
    ov[ink_ref & ink_mod] = (0, 0, 0)
    return res, Image.fromarray(ov)


def font(sz=20):
    try:
        return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', sz)
    except OSError:
        return ImageFont.load_default()


def sheet(cells, cols, path, title=None):
    w = max(c[1].width for c in cells)
    h = max(c[1].height for c in cells)
    rows = (len(cells) + cols - 1) // cols
    top = 40 if title else 0
    o = Image.new('RGB', (cols * w, top + rows * (h + 30)), BG)
    d = ImageDraw.Draw(o)
    if title:
        d.text((10, 8), title, fill=(27, 45, 57), font=font(22))
    for i, (t, im) in enumerate(cells):
        x, y = (i % cols) * w, top + (i // cols) * (h + 30)
        o.paste(im, (x, y + 30))
        d.text((x + 8, y + 6), t, fill=(27, 45, 57), font=font(18))
    o.save(path)


def sheets(out):
    res, ov = metrics(out)
    with open(os.path.join(out, 'metrics.json'), 'w') as f:
        json.dump(res, f, indent=1)
    ref = Image.open(REF).convert('RGB')
    front, _ = flat_bg(os.path.join(out, 'front.png'))
    box = (180, 130, 600, 880)
    sheet([('drawing', ref.crop(box)), ('model', front.crop(box)),
           ('overlay', Image.blend(ref, front, 0.5).crop(box)), ('ink: blue drawing, red model, black both', ov.crop(box))],
          4, os.path.join(out, 'sheet_match.png'), 'Standing front view vs the drawing   ' + json.dumps(res))
    cells = []
    for f, yaw in WAVE_FRAMES:
        im, _ = flat_bg(os.path.join(out, 'chk', f'wave_{f}_{yaw}.png'))
        b = (330, 140, 650, 520) if yaw == 0 else (300, 140, 620, 520)
        cells.append((f'wave frame {f}, yaw {yaw}', im.crop(b).resize((480, 570), Image.LANCZOS)))
    sheet(cells, 3, os.path.join(out, 'sheet_shoulder.png'), 'Raised arm: shoulder and underarm')
    cells = []
    from posing import STRESS
    for name in STRESS:
        for yaw in STRESS_VIEWS:
            im, _ = flat_bg(os.path.join(out, 'chk', f'stress_{name}_{yaw}.png'))
            cells.append((f'{name} {yaw}', im.crop((88, 60, 688, 900)).resize((360, 504), Image.LANCZOS)))
    sheet(cells, 4, os.path.join(out, 'sheet_stress.png'), 'Stress poses')
    return res


if __name__ == '__main__':
    if '--stage=render' in sys.argv:
        render_stage(os.path.abspath(sys.argv[-1]))
        raise SystemExit
    out = os.path.abspath(sys.argv[1])
    os.makedirs(os.path.join(out, 'chk'), exist_ok=True)
    sys.path.insert(0, HERE)
    if '--no-build' not in sys.argv:
        run(os.path.join(HERE, 'build_model.py'), out, '--render')
        run(os.path.join(HERE, 'anim_wave.py'), os.path.join(out, 'doodle.blend'), out)
    run(os.path.abspath(__file__), '--stage=render', out)
    print(json.dumps(sheets(out), indent=1))
