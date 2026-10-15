# Doodle trace pipeline: reference.png -> public/doodle.svg
# Run from any scratch directory (it writes intermediate files there):
#   python3 <repo>/scripts/doodle-trace/matte.py
#   python3 <repo>/scripts/doodle-trace/prep.py 12
#   python3 <repo>/scripts/doodle-trace/build.py 12 <repo>/public/doodle.svg
import os
HERE=os.path.dirname(os.path.abspath(__file__))
from PIL import Image, ImageFilter
import numpy as np
im=np.array(Image.open(os.path.join(HERE,'reference.png')).convert('RGB')).astype(float)
bg=np.load('bg.npy')
H,W,_=im.shape
O=np.array([30,44,56.])  # outline navy
lum=lambda c: c@np.array([.299,.587,.114])
# edge band: opaque pixels touching the background
near=np.zeros_like(bg)
for dy,dx in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,-1),(1,-1),(-1,1)]:
    near|=np.roll(np.roll(bg,dy,0),dx,1)
edge=near&~bg
alpha=np.where(bg,0,255).astype(np.uint8)
# unmix edge pixels against a local background of ~(228,234,234): keep them as outline when dark enough
bgc=np.array([228,234,234.])
a=np.clip((lum(bgc)-lum(im))/(lum(bgc)-lum(O)),0,1)
im[edge]=O
im[bg]=O
alpha[edge&(a<0.3)]=0
rgba=np.dstack([im.clip(0,255).astype(np.uint8),alpha])
Image.fromarray(rgba,'RGBA').save('cut.png')
# crop to the figure with a margin, upscale 3x
ys,xs=np.where(alpha>0); x0,x1,y0,y1=xs.min()-6,xs.max()+7,ys.min()-6,ys.max()+7
print('bbox',x0,y0,x1,y1)
c=Image.fromarray(rgba,'RGBA').crop((x0,y0,x1,y1))
S=3
rgb=c.convert('RGB').resize((c.width*S,c.height*S),Image.LANCZOS)
al=c.getchannel('A').resize((c.width*S,c.height*S),Image.BILINEAR).point(lambda v:255 if v>127 else 0)
# flatten colours: k-means over the figure's pixels only, then clean speckles with a mode filter
import sys
K=int(sys.argv[1]) if len(sys.argv)>1 else 12
A=np.array(rgb).reshape(-1,3).astype(float); M=np.array(al).reshape(-1)>0
X=A[M]; rng=np.random.default_rng(1); smp=X[rng.choice(len(X),60000,replace=False)]
cent=smp[rng.choice(len(smp),K,replace=False)]
# k-means++ style init: spread seeds
cent=[smp[0]]
for _ in range(K-1):
    d=np.min([((smp-c)**2).sum(1) for c in cent],0); cent.append(smp[np.argmax(d)])
cent=np.array(cent)
for _ in range(30):
    lab=np.argmin(((smp[:,None,:]-cent[None])**2).sum(2),1)
    cent=np.array([smp[lab==k].mean(0) if (lab==k).any() else cent[k] for k in range(K)])
lab=np.zeros(len(A),int)
for s0 in range(0,len(A),200000):
    lab[s0:s0+200000]=np.argmin(((A[s0:s0+200000,None,:]-cent[None])**2).sum(2),1)
pal=Image.new('P',(1,1)); flat=[int(v) for c in cent.round().astype(int) for v in c]; pal.putpalette(flat+[0]*(768-len(flat)))
q=Image.fromarray(lab.reshape(rgb.height,rgb.width).astype(np.uint8),'P'); q.putpalette(pal.getpalette())
q=q.filter(ImageFilter.ModeFilter(5))
out=q.convert('RGB'); out.putalpha(al)
out.save('prep.png'); print(out.size, 'palette', [tuple(c) for c in cent.round().astype(int)])
open('bbox.txt','w').write(f'{x0} {y0} {x1} {y1} {S}')
