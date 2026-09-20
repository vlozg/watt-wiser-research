
import glob
import json
import os

os.environ.setdefault("MPLCONFIGDIR","/tmp/mplcfg"); os.makedirs("/tmp/mplcfg",exist_ok=True)
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root
P=os.path.join(ROOT,"research-logs","vi","plaid_samples")+os.sep
FIG=os.path.join(ROOT,"figures")
plt.rcParams.update({"figure.dpi":118,"savefig.dpi":118,"font.size":9,"axes.grid":True,
    "grid.alpha":0.25,"axes.axisbelow":True,"axes.spines.top":False,"axes.spines.right":False})
FS=30000.0; CYC=500
META=json.load(open(os.path.join(ROOT,"research-logs","plaid","metadata_submetered.json")))

def cycles_for(path, ncyc=12):
    pid=os.path.basename(path).split("__")[1][:-4]
    status=META.get(pid,{}).get("appliance",{}).get("status","")
    w=np.loadtxt(path,delimiter=",")
    if w.ndim==1: w=w.reshape(-1,2)
    i,v=w[:,0],w[:,1]
    n=len(i)//CYC
    if n<8: return []
    env=np.abs(i[:n*CYC]).reshape(n,CYC).max(axis=1)
    gv=np.abs(v[:n*CYC]).reshape(n,CYC).max(axis=1)<400
    # window the record according to the captured transition
    if "off-on" in status:  lo,hi=int(n*0.35),n
    elif "on-off" in status: lo,hi=0,int(n*0.65)
    else:                    lo,hi=0,n
    e=env[lo:hi].copy(); g=gv[lo:hi]
    if e.size==0: return []
    keep=(e>0.30*e.max())&g
    idx=np.flatnonzero(keep)
    if len(idx)<3:
        idx=np.flatnonzero(g)
        if len(idx)==0: return []
    if len(idx)>ncyc: idx=idx[np.linspace(0,len(idx)-1,ncyc).astype(int)]
    return [(v[(lo+c)*CYC:(lo+c+1)*CYC], i[(lo+c)*CYC:(lo+c+1)*CYC]) for c in idx]

recs=[]
for f in sorted(glob.glob(P+"*.csv")):
    nm=os.path.basename(f).split("__")[0].replace("_"," ")
    cy=cycles_for(f)
    if len(cy)<3: continue
    recs.append({"name":nm,"cy":cy,"p":float(np.mean([np.mean(a*b) for a,b in cy]))})
recs=[r for r in recs if r["p"]>0.5]
print("usable:", len(recs), "->", ", ".join("%s(%.0fW)"%(r["name"],r["p"]) for r in sorted(recs,key=lambda x:-x["p"])))

# ---------- FIG 5: gallery ----------
order=sorted(recs,key=lambda r:-r["p"])
nr,nc=4,4
fig,axs=plt.subplots(nr,nc,figsize=(13,13))
for ax,r in zip(axs.ravel(),order):
    for vs,is_ in r["cy"]: ax.plot(vs,is_,lw=0.7,alpha=0.55,color="#1f77b4")
    ax.set_title("%s\n%.0f W"%(r["name"],r["p"]),fontsize=9,fontweight="bold")
    ax.axhline(0,color="#bbb",lw=0.6); ax.axvline(0,color="#bbb",lw=0.6)
    ax.set_xlabel("voltage (V)",fontsize=7.5); ax.set_ylabel("current (A)",fontsize=7.5); ax.tick_params(labelsize=7)
for ax in axs.ravel()[len(order):]: ax.axis("off")
fig.suptitle("Figure 5 — V-I trajectories: the fingerprint of a load (PLAID, real measurements, 30 kHz)",fontsize=12.5,fontweight="bold",y=0.997)
fig.text(0.5,0.004,"Each loop = one 60 Hz mains cycle: voltage on x, current on y. Shape is set by the PHYSICS of the load, not its size. "
  "Straight line = resistive. Open ellipse = stored energy (motor). Burst near the peak = switch-mode supply. Lopsided = rectified.",ha="center",fontsize=8.2,color="#555")
fig.tight_layout(rect=[0,0.012,1,0.985]); fig.savefig(FIG+"/fig05_vi_gallery.png",bbox_inches="tight"); plt.close(fig)
print("fig05 done")

# ---------- FIG 6: anatomy ----------
pick=["Water kettle","Compact Fluorescent Lamp","Laptop","Microwave","Vacuum","Fridge"]
notes={
 "Water kettle":"RESISTIVE\nI follows V exactly.\nA near-straight line\nthrough the origin.",
 "Compact Fluorescent Lamp":"NONLINEAR ELECTRONIC\nCurrent arrives in narrow\nspikes at the voltage peaks,\nbriefly reversing sign.\nNothing like the V shape.",
 "Laptop":"SWITCH-MODE SUPPLY\nCurrent flows only in short\nbursts near the peaks:\na rectifier plus a\nreservoir capacitor.",
 "Microwave":"TRANSFORMER\nStrongly asymmetric - the\nnegative half-cycle is\nbarely used. A lopsided\nloop, plus a switching step.",
 "Vacuum":"MOTOR (inductive)\nCurrent LAGS voltage, so the\nloop opens into an ellipse.\nEnclosed area = reactive\npower, not real power.",
 "Fridge":"MOTOR, much smaller\nSame ellipse as the vacuum\nbut a fraction of the current.\nA 60-100 W load is a\nthin sliver on this scale."}
bys={r["name"]:r for r in recs}
fig,axs=plt.subplots(2,3,figsize=(13.5,7.8))
for ax,nm in zip(axs.ravel(),pick):
    r=bys.get(nm)
    if r is None: ax.text(0.5,0.5,nm+"\n(not usable)",ha="center",transform=ax.transAxes); ax.axis("off"); continue
    for vs,is_ in r["cy"]: ax.plot(vs,is_,lw=0.9,alpha=0.5,color="#1f77b4")
    ax.set_title("%s   (%.0f W)"%(nm,r["p"]),fontsize=10,fontweight="bold")
    ax.text(0.02,0.97,notes[nm],transform=ax.transAxes,va="top",ha="left",fontsize=7.4,
            bbox=dict(fc="white",ec="#999",alpha=0.88,pad=2.4))
    ax.axhline(0,color="#bbb",lw=0.6); ax.axvline(0,color="#bbb",lw=0.6)
    ax.set_xlabel("voltage (V)",fontsize=8); ax.set_ylabel("current (A)",fontsize=8)
fig.suptitle("Figure 6 — Reading a trajectory: six archetypes and what each shape means",fontsize=12.5,fontweight="bold",y=0.995)
fig.tight_layout(rect=[0,0,1,0.965]); fig.savefig(FIG+"/fig06_vi_anatomy.png",bbox_inches="tight"); plt.close(fig)
print("fig06 done")

# ---------- FIG 7: harmonic spectra ----------
hpick=["Water kettle","Heater","Incandescent Light Bulb","Fridge","Washing Machine",
       "Microwave","Compact Fluorescent Lamp","Laptop","Vacuum"]
fig,axs=plt.subplots(3,3,figsize=(13.5,8.4))
NH=25
for ax,nm in zip(axs.ravel(),hpick):
    r=bys.get(nm)
    if r is None: ax.axis("off"); continue
    specs=[]
    for _vs,is_ in r["cy"][:8]:
        seg=is_-is_.mean()
        F=np.fft.rfft(seg)
        specs.append(np.abs(F))
    S=np.median(np.array(specs),axis=0)
    if S[1]<=0: ax.axis("off"); continue
    db=20*np.log10(np.maximum(S[:NH+1],1e-12)/S[1])
    k=np.arange(NH+1)
    ax.bar(k,db,color="#4c72b0",width=0.75)
    ax.set_ylim(-90,5); ax.set_xlim(-0.8,NH+0.8)
    thr=3
    ax.set_title("%s  (%.0f W)"%(nm,r["p"]),fontsize=9.5,fontweight="bold")
    ax.set_ylabel("dB rel. fundamental",fontsize=7.5); ax.tick_params(labelsize=7)
    strong=[f"{i}" for i in range(3,NH+1) if db[i]>-40 and i%2==0]
    ax.text(0.97,0.05,"even harmonics > -40 dB: "+((", ".join(strong[:6])) if strong else "none"),
            transform=ax.transAxes,ha="right",fontsize=7,color="#444")
for ax in axs.ravel()[len(hpick):]: ax.axis("off")
for ax in axs.ravel()[-3:]:
    if ax.has_data(): ax.set_xlabel("harmonic order (x 60 Hz)",fontsize=7.5)
fig.suptitle("Figure 7 — Harmonic spectra: the frequency-domain view of the same loads (FFT of one mains cycle)",fontsize=12.5,fontweight="bold",y=0.995)
fig.text(0.5,0.005,"One full 60 Hz cycle transformed, so the window is exactly periodic and leakage vanishes. A clean resistive load puts ALL its energy in the fundamental; "
  "electronics scatter energy up the spectrum. Even harmonics should not exist in a symmetric load - when they do, it means half-wave rectification.",ha="center",fontsize=8,color="#555")
fig.tight_layout(rect=[0,0.015,1,0.965]); fig.savefig(FIG+"/fig07_harmonics.png",bbox_inches="tight"); plt.close(fig)
print("fig07 done")
