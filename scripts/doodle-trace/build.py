# Doodle trace pipeline: reference.png -> public/doodle.svg
# Run from any scratch directory (it writes intermediate files there):
#   python3 <repo>/scripts/doodle-trace/matte.py
#   python3 <repo>/scripts/doodle-trace/prep.py 12
#   python3 <repo>/scripts/doodle-trace/build.py 12 <repo>/public/doodle.svg
import os
HERE=os.path.dirname(os.path.abspath(__file__))
# Layered trace of the reference doodle: an outline-coloured silhouette, then one traced shape per
# flat colour on top. Head and body are separate groups (the head can tilt), pupils are ellipses.
import numpy as np, re, vtracer, os, sys
from PIL import Image
x0,y0,x1,y1,S=map(int,open('bbox.txt').read().split())
q=np.array(Image.open('prep.png').convert('RGBA')).astype(int)
H,W=q.shape[:2]
alpha=q[:,:,3]>0
P={'noise':[(119,141,136),(164,178,185)],'ink':[(8,21,30),(27,46,57),(36,59,71)],'slate':[(61,76,87)],'green':[(66,106,95)],
   'white':[(250,253,252)],'shade':[(203,218,223)],'lime':[(167,211,164),(151,197,145)],'dgreen':[(61,103,73)]}
FILL={'ink':'#1b2d39','slate':'#3d4c57','green':'#426a5f','white':'#fafdfc','shade':'#cbdadf','lime':'#9fcc99','dgreen':'#3d6749'}
cls=np.full((H,W),'',object)
rgb=q[:,:,:3]
for k,cs in P.items():
    for c in cs: cls[(rgb==c).all(2)&alpha]=k
assert (cls[alpha]!='').all(), 'unmapped colours'
# blended edge pixels take the most common real colour around them
def boxsum(m,r):
    c=np.pad(m.astype(np.int32),((r+1,r),(r+1,r))).cumsum(0).cumsum(1)
    return c[2*r+1:,2*r+1:]-c[:-2*r-1,2*r+1:]-c[2*r+1:,:-2*r-1]+c[:-2*r-1,:-2*r-1]
noise=cls=='noise'
names=[k for k in P if k!='noise']
votes=np.stack([boxsum(cls==k,4) for k in names])
best=np.array(names,object)[votes.argmax(0)]
cls[noise]=best[noise]
print('noise px reassigned',noise.sum())
U=lambda x,y:((x-x0)*S,(y-y0)*S)
# ---- pupils: ink pixels near the two eye centres, enclosed by white ----
yy,xx=np.mgrid[0:H,0:W]
pupils=[]
for ox,oy in [(361.7,268.3),(411.7,268.3)]:
    cx,cy=U(ox,oy)
    near=((xx-cx)**2/(5.5*S)**2+(yy-cy)**2/(6.5*S)**2)<=1
    m=near&(cls=='ink')
    ys,xs=np.where(m); pcx,pcy=xs.mean(),ys.mean(); rx=(xs.max()-xs.min()+1)/2; ry=(ys.max()-ys.min()+1)/2
    pupils.append((pcx,pcy,rx,ry)); cls[m]='white'
    print('pupil',round(pcx/S+x0,1),round(pcy/S+y0,1),round(rx/S,1),round(ry/S,1),m.sum())
# ---- head region ----
ox=xx/S+x0; oy=yy/S+y0
ORDER=['slate','green','white','dgreen','lime','shade']
def dil(m,r):
    o=m.copy()
    for _ in range(r):
        n=o.copy(); n[1:]|=o[:-1]; n[:-1]|=o[1:]; n[:,1:]|=o[:,:-1]; n[:,:-1]|=o[:,1:]; o=n
    return o
from PIL import ImageFilter
def smooth(mask):
    # blur + threshold rounds off pixel jaggies so the traced curves come out clean
    im=Image.fromarray((mask*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2.2))
    return np.array(im)>127
def trace(mask,name):
    img=np.where(mask,0,255).astype(np.uint8)
    Image.fromarray(img).save(f'm_{name}.png')
    vtracer.convert_image_to_svg_py(f'm_{name}.png',f'm_{name}.svg',colormode='binary',mode='spline',filter_speckle=int(sys.argv[1]) if len(sys.argv)>1 else 12,
        corner_threshold=60,length_threshold=4.0,splice_threshold=45,path_precision=0)
    s=open(f'm_{name}.svg').read()
    ps=re.findall(r'<path d="([^"]*)" fill="[^"]*" transform="translate\(([-\d.]+),([-\d.]+)\)"',s)
    return [f'<path transform="translate({round(float(tx))} {round(float(ty))})" d="{d.strip()}"/>' for d,tx,ty in ps]
# smooth every layer on the whole figure first, then cut the head out of the smoothed layers,
# so head and body edges line up exactly
layers={'ink':smooth(alpha)}
for i,k in enumerate(ORDER):
    m=cls==k
    m=m|(dil(m,2)&np.isin(cls,ORDER[i+1:]))   # tuck under the colours drawn after it: no hairline seams
    layers[k]=smooth(m)&layers['ink']
# head = everything above the hood's top, plus a trapezoid that follows the jaw down to the chin
slope=(oy-316)*(24/26)
headcut=(oy<316)|((oy<342)&(ox>336+slope)&(ox<444-slope))
svg_groups={}
# body keeps a strip under the chin so a tilted head never opens a gap at the neck
bodycut=~headcut|(headcut&(oy>=330))
for g,cut in [('body',bodycut),('head',headcut)]:
    parts=[]
    for k in ['ink']+ORDER:
        m=layers[k]&cut
        if g=='body' and k=='ink':
            m=m|(layers['ink']&headcut&(oy>=296))  # dark backing behind the jaw: a tilted head shows outline, not a gap
        if m.sum()==0: continue
        parts.append(f'<g fill="{FILL[k]}">'+''.join(trace(m,f'{g}_{k}'))+'</g>')
    svg_groups[g]=''.join(parts)
pup=''.join(f'<ellipse cx="{cx:.0f}" cy="{cy:.0f}" rx="{rx:.0f}" ry="{ry:.0f}"/>' for cx,cy,rx,ry in pupils)
piv=U(390,335)
sh=U(388,858)
inner=(f'<ellipse class="doodle-shadow" cx="{sh[0]:.0f}" cy="{sh[1]:.0f}" rx="{160*S}" ry="{17*S}"/>'
       f'<g data-part="upper"><g data-part="torso">{svg_groups["body"]}</g>'
       f'<g data-part="head" data-pivot="{piv[0]:.0f} {piv[1]:.0f}">{svg_groups["head"]}'
       f'<g data-part="pupils" fill="{FILL["ink"]}"><g class="doodle-blink">{pup}</g></g></g></g>')
open('inner.txt','w').write(inner)
if len(sys.argv)>2:
    # Standalone file for the site: shown as an <img> first, then inlined so the parts can move.
    piv_s=f'{piv[0]:.0f} {piv[1]:.0f}'
    art=inner.replace(f' data-pivot="{piv_s}"','')
    open(sys.argv[2],'w').write(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">'
        f'<!-- Generated by scripts/doodle-trace/build.py. Parts: data-part upper, head (pivot {piv_s}), pupils. -->'
        '<style>.doodle-shadow{fill:#1e2a3a;opacity:.14}</style>'+art+'</svg>')
