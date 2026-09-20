
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
CYC=500
META=json.load(open(os.path.join(ROOT,"research-logs","plaid","metadata_submetered.json")))

def stable_cycles(path, ncyc=40):
    pid=os.path.basename(path).split("__")[1][:-4]
    status=META.get(pid,{}).get("appliance",{}).get("status","")
    w=np.loadtxt(path,delimiter=",")
    if w.ndim==1: w=w.reshape(-1,2)
    i,v=w[:,0],w[:,1]
    n=len(i)//CYC
    if n<10: return None,None
    I=i[:n*CYC].reshape(n,CYC); V=v[:n*CYC].reshape(n,CYC)
    env=np.abs(I).max(axis=1); clean=np.abs(V).max(axis=1)<400
    if "off-on" in status: lo,hi=int(n*0.5),n
    elif "on-off" in status: lo,hi=0,int(n*0.5)
    else: lo,hi=0,n
    e=env[lo:hi].copy(); g=clean[lo:hi]
    if e.size==0: return None,None
    sel=lo+np.flatnonzero((e>0.5*e.max())&g)
    if len(sel)<6: sel=lo+np.flatnonzero(g)
    if len(sel)<6: return None,None
    if len(sel)>ncyc: sel=sel[np.linspace(0,len(sel)-1,ncyc).astype(int)]
    return V[sel], I[sel]

def sync_avg(V,I):
    """align each cycle on the rising voltage zero-crossing, then average"""
    A=[]; B=[]
    for vv,ii in zip(V,I):
        z=np.flatnonzero((vv[:-1]<0)&(vv[1:]>=0))
        if len(z)==0: continue
        s=z[0]
        A.append(np.roll(vv,-s)); B.append(np.roll(ii,-s))
    if len(A)<4: return None,None,0
    return np.mean(A,axis=0), np.mean(B,axis=0), len(A)

recs=[]
for f in sorted(glob.glob(P+"*.csv")):
    nm=os.path.basename(f).split("__")[0].replace("_"," ")
    V,I=stable_cycles(f)
    if V is None: continue
    av,ai,n= sync_avg(V,I)
    if av is None: continue
    p=float(np.mean(av*ai))
    if p<0.5: continue
    recs.append({"name":nm,"v":av,"i":ai,"p":p,"n":n,"V":V,"I":I})
print("records for spectra:", len(recs))

def spectrum(ai,nh=25):
    seg=ai-ai.mean()
    F=np.abs(np.fft.rfft(seg))
    if F[1]<=0: return None,None
    db=20*np.log10(np.maximum(F[:nh+1],1e-12)/F[1])
    thd=np.sqrt(np.sum(F[2:nh+1]**2))/F[1]*100
    return db,thd

for r in recs:
    r["db"],r["thd"]=spectrum(r["i"])
recs=[r for r in recs if r["db"] is not None]
recs.sort(key=lambda r:-r["thd"])
print("sorted by THD:", ", ".join("%s %.0f%%"%(r["name"],r["thd"]) for r in recs))

fig,axs=plt.subplots(4,4,figsize=(13.5,11.2))   # 4x4: show ALL usable captures, kettle included
for ax,r in zip(axs.ravel(),recs):
    k=np.arange(len(r["db"]))
    ax.bar(k,r["db"],color="#4c72b0",width=0.78)
    ax.bar([2,4,6,8,10,12],[r["db"][j] if j<len(r["db"]) else -90 for j in [2,4,6,8,10,12]],
           color="#c44e52",width=0.78)
    ax.set_ylim(-80,4); ax.set_xlim(-0.8,25.8); ax.tick_params(labelsize=7)
    ax.set_title("%s  (%.0f W)"%(r["name"],r["p"]),fontsize=9.5,fontweight="bold")
    ax.set_ylabel("dB rel. fundamental",fontsize=7.5)
    ax.text(0.97,0.90,"THD %.0f%%"%(r["thd"]),transform=ax.transAxes,ha="right",fontsize=8.5,
            fontweight="bold",color="#c44e52",bbox=dict(fc="white",ec="#c44e52",alpha=0.9,pad=1.6))
for ax in axs.ravel()[len(recs):]: ax.axis("off")
for ax in axs.ravel()[-4:]:
    if ax.has_data(): ax.set_xlabel("harmonic order (x 60 Hz)",fontsize=7.5)
fig.suptitle("Figure 7 — Harmonic spectra: the same loads in the frequency domain (FFT of a synchronously-averaged mains cycle)",fontsize=12.3,fontweight="bold",y=0.995)
fig.text(0.5,0.006,"Red bars mark EVEN harmonics, which should be absent from any symmetric load. Panels sorted by total harmonic distortion (THD). A resistive element dumps everything into the fundamental; "
  "electronics scatter it up the spectrum. This is the visual language of speech spectrograms, applied to mains current.",ha="center",fontsize=7.9,color="#555")
fig.tight_layout(rect=[0,0.018,1,0.962]); fig.savefig(FIG+"/fig07_harmonics.png",bbox_inches="tight"); plt.close(fig)
print("fig07 done")

# ---------- FIG 8: waveform -> power bridge ----------
# the PLAID vacuum off-on capture: 12 idle cycles, then motor inrush decaying to the running plateau
w8=np.loadtxt(glob.glob(P+"Vacuum__*.csv")[0],delimiter=",")
if w8.ndim==1: w8=w8.reshape(-1,2)
i8,v8=w8[:,0],w8[:,1]
n8=len(i8)//CYC
I8=i8[:n8*CYC].reshape(n8,CYC); V8=v8[:n8*CYC].reshape(n8,CYC)
oncyc=np.flatnonzero(np.abs(I8).max(axis=1)>1.0)
k0=oncyc[0]; kb=oncyc[len(oncyc)//2]
cyc_p=np.array([np.mean(V8[k]*I8[k]) for k in range(n8)])
fig,ax=plt.subplots(4,1,figsize=(12.5,9.6))
t3=np.arange(3*CYC)/30000*1000
ax[0].plot(t3,V8[k0-1:k0+2].ravel(),lw=0.9,color="#333",label="voltage")
ax[0].plot(t3,I8[k0-1:k0+2].ravel()*30,lw=0.9,color="#d62728",label="current x30")
ax[0].set_title("(a) raw capture — 30 000 samples/s  (3 of %d cycles shown, capture %.2f s)"%(n8,n8/60.0),loc="left",fontsize=9.5,fontweight="bold")
ax[0].set_xlabel("ms"); ax[0].legend(fontsize=8,ncol=2); ax[0].set_ylabel("V / scaled A")
ax[1].plot(np.arange(CYC)/30000*1000,V8[kb],lw=1.0,color="#333",label="voltage")
ax[1].plot(np.arange(CYC)/30000*1000,I8[kb]*30,lw=1.0,color="#d62728",label="current x30")
ax[1].set_title("(b) one running cycle: instantaneous samples. A meter never sees this — it integrates",loc="left",fontsize=9.5,fontweight="bold")
ax[1].set_xlabel("ms"); ax[1].legend(fontsize=8,ncol=2); ax[1].set_ylabel("V / scaled A")
ax[2].plot(np.arange(len(cyc_p))/60.0,cyc_p,marker="o",ms=3.5,lw=1.0,color="#2ca02c")
ax[2].set_title("(c) after one multiplication and one averaging step: WATTS. Sampling rate is now 60 Hz",loc="left",fontsize=9.5,fontweight="bold")
ax[2].set_xlabel("seconds"); ax[2].set_ylabel("W")
ax[3].plot(np.arange(len(cyc_p))/60.0,cyc_p,lw=1.0,color="#999",label="60 Hz (what panel c has)")
for dt_,c_,lab in [(1,"#1f77b4","1 s"),(5,"#ff7f0e","5 s  (the synthetic dataset)"),(60,"#d62728","60 s  (Shelly local API)")]:
    nb=max(1,int(60*dt_))
    x=np.arange(len(cyc_p))//nb*nb/60.0
    u,idx=np.unique(x,return_index=True)
    y=np.array([cyc_p[i:i+nb].mean() for i in idx])
    ax[3].plot(u,y,marker="o",ms=3.5,lw=1.0,color=c_,label=lab)
ax[3].set_title("(d) the same record as the meter would report it — and this is the ENTIRE input to NILM",loc="left",fontsize=9.5,fontweight="bold")
ax[3].set_xlabel("seconds"); ax[3].set_ylabel("W"); ax[3].legend(fontsize=8,ncol=4)
fig.suptitle("Figure 8 — The bridge: how a waveform becomes a number, and what is destroyed at each step",fontsize=12.3,fontweight="bold",y=0.996)
fig.text(0.5,0.004,"Real PLAID vacuum-cleaner capture: an off-on transient; the current clamp saturates at 28 A. Panels (a)-(c) exist only on hardware that exports the raw waveform. A Shelly EM starts at panel (d).",ha="center",fontsize=8,color="#555")
fig.tight_layout(rect=[0,0.012,1,0.982]); fig.savefig(FIG+"/fig08_waveform_to_power.png",bbox_inches="tight"); plt.close(fig)
print("fig08 done")
