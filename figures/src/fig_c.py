
import os
os.environ.setdefault("MPLCONFIGDIR","/tmp/mplcfg"); os.makedirs("/tmp/mplcfg",exist_ok=True)
import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root
D=os.path.join(ROOT,"research-logs","sakunrasilka_nilm-test2")+os.sep
FIG=os.path.join(ROOT,"figures")
plt.rcParams.update({"figure.dpi":118,"savefig.dpi":118,"font.size":9,"axes.grid":True,
    "grid.alpha":0.25,"axes.axisbelow":True,"axes.spines.top":False,"axes.spines.right":False})
raw={c:np.loadtxt(D+f"channel_{c}.dat") for c in range(1,7)}
tend=min(raw[c][-1,0] for c in raw); n=min((raw[c][:,0]<=tend).sum() for c in raw)
t=raw[1][:n,0]; ch={c:raw[c][:n,1] for c in range(1,7)}
NAME={2:"fridge",3:"dish_washer",4:"kettle",5:"washing_machine",6:"monitor"}
COL ={2:"#1f77b4",3:"#ff7f0e",4:"#d62728",5:"#9467bd",6:"#7f7f7f"}
TH=15.0
day=(t//86400).astype(np.int64)
best=None
for d in np.unique(day)[:-1]:
    m=day==d
    if m.sum()<14000: continue
    active=sum(1 for c in [2,3,4,5,6] if (ch[c][m]>TH).mean()>0.005)
    ev=sum((np.abs(np.diff(ch[1][m]))>400).sum() for _ in [0])
    score=active*1000+min(ev,60)
    if best is None or score>best[1]: best=(d,score,active,ev)
print("best day",best)
d0=best[0]; t0d=d0*86400
j0,j1=np.searchsorted(t,t0d),np.searchsorted(t,t0d+86400)
fig,ax=plt.subplots(6,1,figsize=(12.5,9.6),sharex=True)
ax[0].plot(t[j0:j1],ch[1][j0:j1],lw=0.7,color="#111")
ax[0].set_title("AGGREGATE  —  one number per 6 seconds. Everything below is invisible in it.",loc="left",fontsize=9.5,fontweight="bold")
ax[0].set_ylabel("W"); ax[0].set_ylim(0,max(3200,np.percentile(ch[1][j0:j1],99.95)*1.15))
for k,c in enumerate([2,3,4,5,6]):
    a=ax[k+1]; p=ch[c][j0:j1]; st=(p>TH)
    a.fill_between(t[j0:j1],0,p,color=COL[c],lw=0,alpha=0.85)
    d=np.diff(st.astype(np.int8)); on=np.flatnonzero(d==1)+1; off=np.flatnonzero(d==-1)+1
    if st[0]: on=np.r_[0,on]
    if len(on)>len(off): off=np.r_[off,len(st)]
    for s_,e_ in zip(on,off): a.axvspan(t[j0:j1][s_],t[j0:j1][min(e_,len(st)-1)],color=COL[c],alpha=0.13,lw=0)
    ne=len(on)
    a.set_ylabel("W"); a.set_title("GROUND TRUTH  —  "+NAME[c]+"   ON "+f"{100*st.mean():.1f}"+"% of the day, "+str(ne)+" events",loc="left",fontsize=8.6,fontweight="bold",color=COL[c])
    a.set_ylim(0,max(60,np.percentile(p,99.5)*1.25))
ax[-1].set_xlabel("unix time")
fig.suptitle("Figure 3 — One day, unrolled: the aggregate is the sum, and the sum is what hides the parts",fontsize=12,fontweight="bold",y=0.997)
fig.text(0.5,0.004,"UK-DALE, 24 h at 6 s. Shaded bands mark ON intervals. The washing machine is the instructive one: a long multi-stage cycle that no single step size can describe.",
         ha="center",fontsize=7.8,color="#555")
fig.tight_layout(rect=[0,0.012,1,0.985]); fig.savefig(FIG+"/fig03_one_day_zoom.png",bbox_inches="tight"); plt.close(fig)
print("fig03 rebuilt on day",d0)
