#!/usr/bin/env python3
"""Render a 1200x630 preview card for every queue item into .social/cards/<id>.jpg.
Run from the repo root. Screenshots for calculators come from /tmp/claude-0/shots (Playwright)."""
import json, os, textwrap
from PIL import Image, ImageDraw, ImageFont, ImageFilter
NAVY=(19,32,61); TEAL=(38,153,137); ORANGE=(226,112,64); CREAM=(246,243,236); WHITE=(255,255,255)
XB='/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'; B='/usr/share/fonts/opentype/inter/Inter-Bold.otf'; SB='/usr/share/fonts/opentype/inter/Inter-SemiBold.otf'
SHOTS=os.environ.get('SHOTS','/tmp/claude-0/shots')
F=lambda p,s: ImageFont.truetype(p,s)
PIN=(30,575,970,1300)
SRC={
 'bf1':('pins/bundle-a.jpg',PIN),'bf2':('pins/bundle-a.jpg',PIN),
 'bf3':('social-assets/forum-pl-budzet-v3.jpg',(40,470,1160,1250)),'bf4':('social-assets/forum-de-haushaltsbuch-v3.jpg',(40,470,1160,1250)),
 'bf5':('pins/debt-a.jpg',PIN),
 'calc-house':('pins/house-affordability-calculator-a.jpg',PIN),'calc-rentbuy':('pins/rent-vs-buy-calculator-a.jpg',PIN),'calc-car':('pins/car-affordability-calculator-a.jpg',PIN),
 'g-snowball':('pins/debt-a.jpg',PIN),'g-503020':('pins/budget-a.jpg',PIN),'g-sinking':('pins/savings-a.jpg',PIN),
 'g-emergency':('pins/emergency-a.jpg',PIN),'g-minpay':('pins/creditcard-a.jpg',PIN),
 'g-zerobased':('pins/zerobased-a.jpg',PIN),'g-couples':('pins/couples-a.jpg',PIN),
 'g-networth':('pins/networth-a.jpg',PIN),'g-52week':('pins/challenge-a.jpg',PIN),
 'g-10k':('pins/challenge-a.jpg',PIN),'g-reset':('pins/simple-a.jpg',PIN),'g-paycheck':('pins/paycheck-a.jpg',PIN),
 'g-xmas':('pins/christmas-a.jpg',PIN),'g-market':('pins/pricing-a.jpg',PIN),'g-etsyfees':('pins/etsyseller-a.jpg',PIN),
 'g-freelance':('pins/freelancer-a.jpg',PIN),'g-weddingcut':('pins/guestlist-a.jpg',PIN),
 'g-notion':('pins/notion-budget-a.jpg',(60,590,640,1000)),'g-coloring':('pins/debtcolor-a.jpg',PIN),
 't-debt':('pins/debt-a.jpg',PIN),'t-budget':('pins/budget-a.jpg',PIN),'t-club':('pins/club-a.jpg',PIN),'t-notion-free':('pins/notion-savings-a.jpg',(60,590,640,1000)),
 'pl-budzet':('social-assets/forum-pl-budzet-v3.jpg',(40,470,1160,1250)),
 'pl-zdrowotna':('pins/jdg-cover.jpg',(0,230,900,720)),'pl-ryczalt':('pins/jdg-cover.jpg',(0,230,900,720)),'pl-nierej':('pins/jdg-cover.jpg',(0,230,900,720)),
 'pl-jdg':('pins/jdg-cover.jpg',(0,230,900,720)),'pl-koperty':('social-assets/forum-pl-budzet-v3.jpg',(40,470,1160,1250)),'pl-52':('pl/img/pl-lite.jpg',(60,250,760,620)),
 'de-haushaltsbuch':('social-assets/forum-de-haushaltsbuch-v3.jpg',(40,470,1160,1250)),
}
for k in ['calc-house','calc-rentbuy','calc-car','calc-snowball','calc-sinking','calc-503020','calc-etsy','calc-selfemp','calc-wedding']:
    SRC[k]=(f'{SHOTS}/{k}.png',(0,0,1040,1250))
SRC['pl-kula']=(f'{SHOTS}/pl-kula.png',(0,0,1040,1000))
TXT={  # pill, headline, sub
 'bf1':('BLACK FRIDAY · −25%','Every money spreadsheet 25% off','Code BLACKFRIDAY25 · until 1 Dec'),
 'bf2':('BLACK FRIDAY · −25%','2027 Money Reset Bundle','4 spreadsheets · code BLACKFRIDAY25'),
 'bf3':('BLACK FRIDAY · −25%','Arkusze budżetowe 25% taniej','Kod BLACKFRIDAY25 · do 1 grudnia'),
 'bf4':('BLACK FRIDAY · −25%','Haushaltsbuch 2027: 25 % günstiger','Code BLACKFRIDAY25 · bis 1. Dez.'),
 'bf5':('LAST DAY · −25%','Black Friday ends tonight','Code BLACKFRIDAY25 on every sheet'),
 'calc-snowball':('FREE CALCULATOR','Your debt-free date in 10 seconds','Snowball vs avalanche, no sign-up'),
 'calc-sinking':('FREE CALCULATOR','How much to save each month','Sinking funds for every big cost'),
 'calc-503020':('FREE CALCULATOR','Does 50/30/20 work on your pay?','Needs, wants and savings in seconds'),
 'calc-etsy':('FREE CALCULATOR','What you really keep per Etsy sale','All fees + Offsite Ads, per order'),
 'calc-selfemp':('FREE CALCULATOR','How much tax to set aside','US self-employed & 1099'),
 'calc-wedding':('FREE CALCULATOR','Your wedding budget, split by category','Total + guest count = full plan'),
 'calc-house':('FREE CALCULATOR','How much house can you afford?','Based on take-home pay'),
 'calc-rentbuy':('FREE CALCULATOR','Rent or buy: which is cheaper?','Find your break-even'),
 'calc-car':('FREE CALCULATOR','How much car can you afford?','The 20/4/10 rule, checked'),
 'g-snowball':('WORKED EXAMPLE','Snowball vs avalanche: which wins?','4 debts, same €400 a month'),
 'g-503020':('WORKED EXAMPLE','50/30/20 on a €2,800 salary','Needs, wants, savings in euros'),
 'g-sinking':('MONEY GUIDE','15 sinking funds most budgets forget','+ how much to save each month'),
 'g-emergency':('MONEY GUIDE','How big should your emergency fund be?','Find your number in 5 steps'),
 'g-minpay':('MONEY GUIDE','Minimum payments: 9 years of debt','€3,000 at 22% APR, worked out'),
 'g-zerobased':('WORKED EXAMPLE','Give every euro a job','Zero-based budget on €2,600'),
 'g-couples':('WORKED EXAMPLE','Split bills fairly as a couple','50/50 vs by income'),
 'g-networth':('MONEY GUIDE','Calculate your net worth','Worked example + what to count'),
 'g-52week':('2027 CHALLENGE','52-week savings challenge','€1,378 · €5,000 · €10,000 plans'),
 'g-10k':('2027 PLAN','Save €10,000 in 2027','€833 a month, month by month'),
 'g-reset':('NEW YEAR','January money reset: 7 steps','Start 2027 with a clean plan'),
 'g-paycheck':('MONEY GUIDE','Stop running out before payday','Budget by paycheck'),
 'g-xmas':('CHRISTMAS','A calm Christmas budget','€900 worked example + gift list'),
 'g-market':('FOR MAKERS','Price handmade gifts for a profit','Christmas market formula'),
 'g-etsyfees':('ETSY SELLERS','How much does Etsy take per sale?','13% normally, up to 28%'),
 'g-freelance':('FREELANCERS','Bookkeeping without an accountant','What to track each month'),
 'g-weddingcut':('WEDDING','Cut the guest list without drama','What 30 fewer guests save'),
 'g-notion':('FREE TEMPLATE','Free Notion budget templates','Duplicate in one click'),
 'g-coloring':('DEBT PAYOFF','Colour in your debt payoff','100 squares, 1% each'),
 't-debt':('GOOGLE SHEETS + EXCEL','Debt payoff spreadsheet','See your debt-free month'),
 't-budget':('GOOGLE SHEETS + EXCEL','Your whole 2027 budget','Planned vs actual, every month'),
 't-club':('MEMBERSHIP','Every money spreadsheet, €5/month','New sheets every month'),
 't-notion-free':('FREE TEMPLATES','5 free Notion finance templates','Budget, debt, savings, wedding'),
 'pl-budzet':('DARMOWY ARKUSZ','Budżet domowy 2027 w złotówkach','Excel i Arkusze Google, bez rejestracji'),
 'pl-zdrowotna':('JDG 2026','Ile wynosi składka zdrowotna?','Ryczałt, liniowy i skala z przykładami'),
 'pl-ryczalt':('JDG 2026','Ryczałt czy liniowy?','Przykład z liczbami dla freelancera'),
 'pl-nierej':('LIMIT 2026','Działalność nierejestrowana','10 813,50 zł na kwartał: zasady'),
 'pl-koperty':('BUDŻET DOMOWY','Metoda kopertowa w Excelu','Przykład na 6000 zł netto'),
 'pl-52':('WYZWANIE 2027','Wyzwanie 52 tygodni','1378 zł · 6890 zł · 13 780 zł'),
 'pl-kula':('SPŁATA DŁUGÓW','Kula śnieżna czy lawina?','Przykład z liczbami'),
 'pl-jdg':('EXCEL DLA JDG','Arkusz JDG 2027','ZUS, zdrowotna, zaliczki, podatek'),
 'de-haushaltsbuch':('KOSTENLOS','Haushaltsbuch 2027 in Euro','Excel & Google Sheets, ohne Anmeldung'),
}
def wrap(d, text, font, width):
    words=text.split(); lines=[]; cur=''
    for w in words:
        t=(cur+' '+w).strip()
        if d.textlength(t,font=font)<=width: cur=t
        else: lines.append(cur); cur=w
    lines.append(cur); return lines
def mock(path, box):
    im=Image.open(path).convert('RGB')
    if box: im=im.crop(box)
    W,H=580,540
    s=max(W/im.width, H/im.height) if im.width/im.height<W/H*0.8 else W/im.width
    im=im.resize((int(im.width*W/im.width), int(im.height*W/im.width)),Image.LANCZOS)
    im=im.crop((0,0,W,min(H,im.height)))
    m=Image.new('L',im.size,0); ImageDraw.Draw(m).rounded_rectangle([0,0,*im.size],22,fill=255)
    o=Image.new('RGBA',im.size,(0,0,0,0)); o.paste(im,(0,0),m); return o
def card(k):
    pill,head,sub=TXT[k]; path,box=SRC[k]
    c=Image.new('RGBA',(1200,630),CREAM+(255,)); d=ImageDraw.Draw(c)
    d.rectangle([0,0,1200,10],fill=NAVY)
    mk=mock(path,box).rotate(2,expand=True,resample=Image.BICUBIC)
    x=1200-mk.width-40; y=max(30,(630-mk.height)//2)
    sh=Image.new('RGBA',(mk.width+100,mk.height+100),(0,0,0,0)); a=mk.split()[3].point(lambda v:int(v*.45))
    s=Image.new('RGBA',mk.size,(0,0,0,255)); s.putalpha(a); sh.paste(s,(50,65),s); sh=sh.filter(ImageFilter.GaussianBlur(22))
    c.alpha_composite(sh,(x-50,y-50)); c.alpha_composite(mk,(x,y))
    pf=F(B,24); pw=d.textlength(pill,font=pf)
    col=ORANGE if 'BLACK' in pill or 'LAST' in pill else TEAL
    d.rounded_rectangle([56,64,56+pw+40,108],22,fill=col); d.text((76,71),pill,font=pf,fill=WHITE)
    size=64
    while True:
        hf=F(XB,size); lines=wrap(d,head,hf,470)
        if len(lines)<=3 or size<=48: break
        size-=4
    yy=150
    for l in lines: d.text((56,yy),l,font=hf,fill=NAVY); yy+=int(size*1.12)
    yy+=14
    for l in wrap(d,sub,F(SB,30),470): d.text((56,yy),l,font=F(SB,30),fill=ORANGE); yy+=40
    d.text((56,548),'digitalworlds.cc',font=F(XB,30),fill=NAVY)
    c.convert('RGB').save(f'.social/cards/{k}.jpg',quality=88)
if __name__=='__main__':
    q=json.load(open('.social/queue.json'))
    for it in q: card(it['id'])
    print('cards', len(q))
