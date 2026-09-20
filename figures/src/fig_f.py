
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
best=None
for f in sorted(glob.glob(P+"*.csv")):
    nm=os.path.basename(f).split("__")[0].replace("_"," ")
    w=np.loadtxt(f,delimiter=","); i,v=w[:,0],w[:,1]
    n=len(i)//CYC
    if n<20: continue
    I=i[:n*CYC].reshape(n,CYC); V=v[:n*CYC].reshape(n,CYC)
    clean=np.abs(V).max(axis=1)<400
    if clean.sum()<20: continue
    pc=np.array([np.mean(V[k]*I[k]) for k in range(n)])
    pc=pc[clean]
    spread=(np.percentile(pc,95)-np.percentile(pc,5))
    if best is None or spread>best[0]: best=(spread,nm,f,pc.max())
print("chosen:",best[1],"of",best[3],"W, spread",round(best[0],1))

f=best[2]
w=np.loadtxt(f,delimiter=","); i,v=w[:,0],w[:,1]
n=len(i)//CYC
I=i[:n*CYC].reshape(n,CYC); V=v[:n*CYC].reshape(n,CYC)
clean=np.abs(V).max(axis=1)<400
pc=np.array([np.mean(V[k]*I[k]) for k in range(n)])
secs=np.arange(n)/60.0
nm=best[1]

fig,ax=plt.subplots(4,1,figsize=(12.5,9.8))
k0=int(np.argmax(np.abs(pc)[clean]))
t3=np.arange(3*CYC)/30000*1000
k3=max(0,min(n-3,k0-1))
ax[0].plot(t3,V[k3:k3+3].ravel(),lw=0.9,color="#333",label="voltage (V)")
ax[0].plot(t3,I[k3:k3+3].ravel()*30,lw=0.9,color="#d62728",label="current (A) x30")
ax[0].set_title("(a) raw hardware capture — 30 000 samples per second",loc="left",fontsize=9.5,fontweight="bold")
ax[0].set_xlabel("ms"); ax[0].legend(fontsize=8,ncol=2); ax[0].set_ylabel("V  /  scaled A")
ax[1].plot(np.arange(CYC)/30000*1000,V[k0],lw=1.0,color="#333",label="voltage (V)")
ax[1].plot(np.arange(CYC)/30000*1000,I[k0]*30,lw=1.0,color="#d62728",label="current (A) x30")
ax[1].set_title("(b) one mains cycle — every quantity a NILM algorithm would love is here, and none of it survives",loc="left",fontsize=9.5,fontweight="bold")
ax[1].set_xlabel("ms"); ax[1].legend(fontsize=8,ncol=2); ax[1].set_ylabel("V  /  scaled A")
ax[2].plot(secs,pc/1000.0,lw=1.1,color="#2ca02c")
ax[2].set_title("(c) one multiply + one average per cycle = WATTS. 30 000 Hz collapses to 60 Hz here and it is irreversible",loc="left",fontsize=9.5,fontweight="bold")
ax[2].set_xlabel("seconds"); ax[2].set_ylabel("kW")
ax[3].plot(secs,pc/1000.0,lw=0.9,color="#bbb",label="60 Hz — what panel (c) has")
for dt_,c_,lab in [(1,"#1f77b4","1 s"),(5,"#ff7f0e","5 s  (the synthetic dataset)")]:
    nb=max(1,int(60*dt_)); x=np.arange(n)//nb*nb/60.0
    u,idx=np.unique(x,return_index=True)
    y=np.array([pc[j:j+nb].mean() for j in idx])
    ax[3].plot(u,y/1000.0,marker="o",ms=4,lw=1.1,color=c_,label=lab)
ax[3].set_title("(d) the same record as a meter would report it — the entire input to NILM",loc="left",fontsize=9.5,fontweight="bold")
ax[3].set_xlabel("seconds"); ax[3].set_ylabel("kW"); ax[3].legend(fontsize=8,ncol=4)
ax[3].annotate("60 s cannot even be drawn:\nthis capture is only %.1f s long"%(n/60.0),xy=(0.5,0.5),
   xycoords="axes fraction",ha="center",fontsize=9,color="#c44e52",fontweight="bold")
fig.suptitle("Figure 8 — The bridge: how a waveform becomes a number, and what is destroyed at each step  [%s]"%nm,fontsize=12,fontweight="bold",y=0.996)
fig.text(0.5,0.004,"Real PLAID capture. Panels (a)-(c) exist only on hardware that exports the raw waveform; a Shelly EM starts at panel (d). Waveform archives are seconds long, smart-meter archives are years long - and no public dataset gives you both at once.",ha="center",fontsize=7.8,color="#555")
fig.tight_layout(rect=[0,0.012,1,0.98]); fig.savefig(FIG+"/fig08_waveform_to_power.png",bbox_inches="tight"); plt.close(fig)
print("fig08 redone")
