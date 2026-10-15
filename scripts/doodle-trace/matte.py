# Doodle trace pipeline: reference.png -> public/doodle.svg
# Run from any scratch directory (it writes intermediate files there):
#   python3 <repo>/scripts/doodle-trace/matte.py
#   python3 <repo>/scripts/doodle-trace/prep.py 12
#   python3 <repo>/scripts/doodle-trace/build.py 12 <repo>/public/doodle.svg
import os
HERE=os.path.dirname(os.path.abspath(__file__))
from PIL import Image
import numpy as np
im=np.array(Image.open(os.path.join(HERE,'reference.png')).convert('RGB')).astype(int)
H,W,_=im.shape
mn=im.min(2); B=im[:,:,2]
bglike=(mn>180)&(B<=247)
def flood(seed, allow):
    m=seed&allow
    while True:
        n=m.copy()
        n[1:]|=m[:-1]; n[:-1]|=m[1:]; n[:,1:]|=m[:,:-1]; n[:,:-1]|=m[:,1:]
        n&=allow
        if (n==m).all(): return m
        m=n
seed=np.zeros((H,W),bool); seed[0]=seed[-1]=True; seed[:,0]=seed[:,-1]=True
bg=flood(seed,bglike)
# second pass: slightly bluer light pixels reachable from the background (the thin slivers between
# the arms and the body). Face and tee are enclosed by outlines, so the flood never reaches them.
G=im[:,:,1]
loose=(mn>175)&(B<=251)&(G<=251)
bg=flood(bg,loose|bg)
# the slivers of background between each sleeve and the body are closed off by antialiasing,
# so mark the light pixels in those two narrow gaps (above the cuffs) explicitly
for gx0,gx1 in [(285,311),(465,496)]:
    gap=np.zeros_like(bg); gap[480:567,gx0:gx1]=True
    bg|=gap&(mn>170)
# remaining bg-like components that are large (enclosed background pockets)
rest=bglike&~bg
print('bg px',bg.sum(),'rest bglike px',rest.sum())
np.save('bg.npy',bg)
vis=im.copy().astype(np.uint8); vis[bg]=[255,0,255]
Image.fromarray(vis).save('bgmask.png')
r=np.zeros_like(vis); r[rest]=[255,255,0]; Image.fromarray(r).save('rest.png')
