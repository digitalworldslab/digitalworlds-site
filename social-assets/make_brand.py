from PIL import Image, ImageDraw, ImageFont, ImageFilter
NAVY=(19,32,61); TEAL=(38,153,137); ORANGE=(234,128,78); WHITE=(255,255,255); CREAM=(246,243,236)
B='/usr/share/fonts/opentype/inter/Inter-Bold.otf'; XB='/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'; M='/usr/share/fonts/opentype/inter/Inter-SemiBold.otf'
import os
XB = XB if os.path.exists(XB) else B
def f(p,s): return ImageFont.truetype(p,s)
def card(img, w, radius=28):
    img=img.convert('RGB'); img=img.resize((w,int(img.height*w/img.width)),Image.LANCZOS)
    m=Image.new('L',img.size,0); ImageDraw.Draw(m).rounded_rectangle([0,0,*img.size],radius,fill=255)
    out=Image.new('RGBA',img.size); out.paste(img,(0,0),m); return out
def shadow_paste(bg, im, xy, angle=0):
    if angle: im=im.rotate(angle,expand=True,resample=Image.BICUBIC)
    sh=Image.new('RGBA',(im.width+120,im.height+120),(0,0,0,0))
    a=im.split()[3].point(lambda v: int(v*0.55))
    s=Image.new('RGBA',im.size,(0,0,0,255)); s.putalpha(a); sh.paste(s,(60,80),s)
    sh=sh.filter(ImageFilter.GaussianBlur(28))
    bg.alpha_composite(sh,(xy[0]-60,xy[1]-60)); bg.alpha_composite(im,xy)
# ---------- banner 3000x1000
W,H=3000,1000
bg=Image.new('RGBA',(W,H),NAVY+(255,))
d=ImageDraw.Draw(bg)
for i in range(H):  # subtle diagonal glow
    pass
d.ellipse([1500,-500,3600,1400],fill=(27,48,88))
d.rectangle([0,H-18,W,H],fill=ORANGE)
debt=Image.open('pins/debt-a.jpg').crop((40,590,960,1300))
bud=Image.open('pins/budget-a.jpg').crop((40,585,960,1250))
pl=Image.open('social-assets/forum-pl-budzet-v3.jpg').crop((60,480,1140,1240))
shadow_paste(bg, card(pl,560), (1760,230), angle=5)
shadow_paste(bg, card(bud,560), (2330,180), angle=-3)
shadow_paste(bg, card(debt,600), (2020,330), angle=1)
d=ImageDraw.Draw(bg)
X=640
d.rounded_rectangle([X,200,X+560,262],31,fill=TEAL)
d.text((X+30,207),"GOOGLE SHEETS + EXCEL",font=f(B,40),fill=WHITE)
d.text((X,300),"Budget & debt",font=f(XB,124),fill=WHITE)
d.text((X,440),"spreadsheets",font=f(XB,124),fill=ORANGE)
d.text((X,610),"+ free money calculators",font=f(M,60),fill=(214,222,235))
d.text((X,700),"EN · PL · DE",font=f(M,44),fill=(160,175,200))
bg.convert('RGB').save('social-assets/banner-v2.jpg',quality=90)
# ---------- avatar 1000x1000
A=Image.new('RGBA',(1000,1000),NAVY+(255,)); d=ImageDraw.Draw(A)
d.rounded_rectangle([170,190,830,810],60,fill=WHITE)
d.rounded_rectangle([170,190,830,330],60,fill=TEAL); d.rectangle([170,280,830,330],fill=TEAL)
for y in (430,530,630,730): d.line([210,y,790,y],fill=(220,226,234),width=8)
for x in (390,610): d.line([x,330,x,790],fill=(220,226,234),width=8)
for x,h in ((250,170),(320,260),(460,200),(530,330),(670,280),(740,420)):
    d.rounded_rectangle([x-30,790-h,x+30,790],12,fill=ORANGE if x in (530,740) else TEAL)
d.text((500,262),"DWL",font=f(XB,96),fill=WHITE,anchor="mm")
A.convert('RGB').save('social-assets/avatar-v2.jpg',quality=92)
# preview like Bluesky: banner 600x200, avatar circle 90px overlapping bottom-left
pv=Image.new('RGB',(600,330),WHITE); bn=Image.open('social-assets/banner-v2.jpg').resize((600,200)); pv.paste(bn,(0,0))
av=Image.open('social-assets/avatar-v2.jpg').resize((90,90)); m=Image.new('L',(90,90),0); ImageDraw.Draw(m).ellipse([0,0,90,90],fill=255)
ImageDraw.Draw(pv).ellipse([10,148,106,244],fill=WHITE); pv.paste(av,(13,151),m)
ImageDraw.Draw(pv).text((14,255),"Digital Worlds Lab",font=f(XB,30),fill=(0,0,0))
pv.save('/tmp/claude-0/pv.png')
