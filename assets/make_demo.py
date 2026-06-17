#!/usr/bin/env python3
"""Animated GIF for lying-spreadsheets-ii. Terminal output is REAL output from
poc/lying_xlsx.py and defense/detect_xlsx.py on the C3 (fully-consistent) tamper."""
from PIL import Image, ImageDraw, ImageFont
import os
W,H=1200,700
BG=(13,17,23); FG=(201,209,217); MUT=(139,148,158); GRN=(63,185,80)
CYN=(88,166,255); YEL=(210,153,34); RED=(248,81,73); CHROME=(22,27,34)
MENLO="/System/Library/Fonts/Menlo.ttc"; ARIALB="/System/Library/Fonts/Supplemental/Arial Bold.ttf"; ARIAL="/System/Library/Fonts/Supplemental/Arial.ttf"
def f(p,s,i=0):
    try: return ImageFont.truetype(p,s,index=i)
    except Exception: return ImageFont.truetype(p,s)
mono=f(MENLO,21); mono_s=f(MENLO,17); title=f(ARIALB,44); subt=f(ARIAL,25); small=f(ARIAL,18)
frames=[]; durations=[]
def base():
    img=Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(img)
    d.rectangle([0,0,W,44],fill=CHROME)
    for i,c in enumerate([(255,95,86),(255,189,46),(39,201,63)]): d.ellipse([22+i*26,15,36+i*26,29],fill=c)
    return img,d
def wt(d,t): w=d.textlength(t,font=mono_s); d.text(((W-w)/2,14),t,font=mono_s,fill=MUT)
def add(img,ms): frames.append(img.convert("P",palette=Image.ADAPTIVE,colors=128)); durations.append(ms)
def card(lines,ms=1600,tt="lying-spreadsheets II"):
    img,d=base(); wt(d,tt); total=sum(h for *_,h in lines); y=(H+44-total)/2
    for text,fnt,col,lh in lines:
        w=d.textlength(text,font=fnt); d.text(((W-w)/2,y),text,font=fnt,fill=col); y+=lh
    add(img,ms)
def term(tt,lines,typing=None,cursor=True,y0=70):
    img,d=base(); wt(d,tt); y=y0
    for text,col in lines: d.text((40,y),text,font=mono,fill=col); y+=30
    if typing is not None:
        text,col=typing; d.text((40,y),text,font=mono,fill=col)
        if cursor:
            cx=40+d.textlength(text,font=mono); d.rectangle([cx+2,y+3,cx+12,y+25],fill=FG)
    return img
def type_line(tt,prev,prefix,body,col,step=3,ms=26,y0=70):
    i=0
    while i<=len(body): add(term(tt,prev,typing=(prefix+body[:i],col),y0=y0),ms); i+=step
    add(term(tt,prev,typing=(prefix+body,col),cursor=False,y0=y0),250)

# A title
card([("Lying Spreadsheets II",title,FG,66),("Extraction-time data falsification",subt,CYN,50),
      ("",subt,FG,18),("github.com/legalrealist/lying-spreadsheets-ii",small,MUT,30)],1600)
# B deception (real numbers)
card([("Loan covenant: Debt / EBITDA must be ≤ 3.0×",subt,FG,54),
      ("",small,FG,10),
      ("Human opens in Excel → recalculates → 3.8×  BREACH",subt,RED,50),
      ("Pipeline reads with pandas → cached 2.5×  COMPLIANT",subt,YEL,50),
      ("",small,FG,10),
      ("Same file. The LLM faithfully approves the attacker's number.",small,MUT,30)],2600)
# C the C3 twist
card([("C3: the attacker fakes the components too — fully consistent.",subt,FG,52),
      ("",small,FG,8),
      ("Cross-checking the extracted table passes every time.",small,MUT,32),
      ("Only recomputing from the raw inputs catches it.",small,GRN,32)],2400)
# D detector terminal (real output)
T="zsh — the detector"
type_line(T,[],"$ ","pip install -r requirements.txt",FG)
l=[("$ pip install -r requirements.txt",FG)]
type_line(T,l,"$ ","python defense/detect_xlsx.py covenant_C3.xlsx",FG)
l=[("$ pip install -r requirements.txt",FG),("$ python defense/detect_xlsx.py covenant_C3.xlsx",FG)]
add(term(T,l,cursor=False),350)
det=[
 ("TAMPERING SUSPECTED -- 5 cell(s) where cache != recomputation:",RED),
 ("  B3: cached=142  recomputed=90",FG),
 ("  B5: cached=152  recomputed=100",FG),
 ("  B7: cached=2.5  recomputed=3.8",FG),
 ("  B9: cached='COMPLIANT'  recomputed='BREACH'",FG),
]
acc=list(l)
for ln in det: acc.append(ln); add(term(T,acc,cursor=False),300)
add(term(T,acc,cursor=False),900)
acc+=[("",FG),("$ python -m pytest -q",FG),("7 passed",GRN)]
add(term(T,acc,cursor=False),1800)
# E end
card([("The one general defense: compare the readers.",subt,FG,50),
      ("rendered (human) vs extracted (pipeline) — never reason about the extract alone",small,MUT,40),
      ("",subt,FG,12),
      ("github.com/legalrealist/lying-spreadsheets-ii",small,CYN,30)],2400)

out=os.path.join(os.path.dirname(__file__),"demo.gif")
frames[0].save(out,save_all=True,append_images=frames[1:],duration=durations,loop=0,optimize=True,disposal=2)
print(f"wrote {out} ({len(frames)} frames, {os.path.getsize(out)//1024} KB)")
