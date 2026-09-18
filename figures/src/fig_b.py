
import os
os.environ.setdefault("MPLCONFIGDIR","/tmp/mplcfg"); os.makedirs("/tmp/mplcfg",exist_ok=True)
import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Patch
ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root
D=os.path.join(ROOT,"research-logs","sakunrasilka_nilm-test2")+os.sep
FIG=os.path.join(ROOT,"figures")
plt.rcParams.update({"figure.dpi":118,"savefig.dpi":118,"font.size":9,"axes.grid":True,
    "grid.alpha":0.25,"axes.axisbelow":True,"axes.spines.top":False,"axes.spines.right":False})

labels=dict(l.split() for l in open(D+"labels.dat"))
raw={c:np.loadtxt(D+f"channel_{c}.dat") for c in range(1,7)}
tend=min(raw[c][-1,0] for c in raw)
n=min((raw[c][:,0]<=tend).sum() for c in raw)
t=raw[1][:n,0]
ch={c:raw[c][:n,1] for c in range(1,7)}
assert all(len(ch[c])==n for c in ch), "still ragged"
print("truncated to common window:", n, "samples,", round((t[-1]-t[0])/86400,2), "days")
NAME={2:"fridge",3:"dish_washer",4:"kettle",5:"washing_machine",6:"monitor"}
COL ={2:"#1f77b4",3:"#ff7f0e",4:"#d62728",5:"#9467bd",6:"#7f7f7f"}
TH=15.0
day=(t//86400).astype(np.int64)
# busiest 7-day span
best=None
for d in np.unique(day)[:-7]:
    m=(day>=d)&(day<d+7)
    if m.sum()<90000: continue
    r=np.percentile(ch[1][m],99.7)-np.percentile(ch[1][m],5)
    if best is None or r>best[1]: best=(d,r)
d0=best[0]; t0=d0*86400
i0,i1=np.searchsorted(t,t0),np.searchsorted(t,t0+7*86400)
print("week",d0,"-",d0+7)

# ---------- FIG 2: the NILM poster ----------
fig,ax=plt.subplots(6,1,figsize=(12.5,9.4),sharex=True)
ax[0].plot(t[i0:i1],ch[1][i0:i1],lw=0.55,color="#111")
ax[0].set_ylabel("W"); ax[0].set_title("AGGREGATE  (what the meter sees)  —  channel_1",loc="left",fontsize=9.5,fontweight="bold")
ax[0].set_ylim(0,np.percentile(ch[1][i0:i1],99.95)*1.12)
ax[0].axhspan(0,30,color="red",alpha=0.13,zorder=0)
ax[0].text(0.002,0.06,"blind below 30 VA (Shelly floor)",transform=ax[0].transAxes,fontsize=7.5,color="#a00")
for k,c in enumerate([2,3,4,5,6]):
    a=ax[k+1]
    a.fill_between(t[i0:i1],0,ch[c][i0:i1],color=COL[c],lw=0,alpha=0.85)
    a.set_ylabel("W"); a.set_title("GROUND TRUTH  —  "+NAME[c],loc="left",fontsize=8.6,fontweight="bold",color=COL[c])
    a.set_ylim(0,max(60,np.percentile(ch[c][i0:i1],99.5)*1.25))
ax[-1].set_xlabel("time")
fig.suptitle("Figure 2 — The NILM poster: one aggregate signal, five appliances hiding inside it",fontsize=12,fontweight="bold",y=0.997)
fig.text(0.5,0.004,"UK-DALE, 7 days at 6 s. The top trace is what a whole-home meter records. The five below are the answer, obtained with separate clamps on each appliance.",
         ha="center",fontsize=7.8,color="#555")
fig.tight_layout(rect=[0,0.012,1,0.985]); fig.savefig(FIG+"/fig02_nilm_poster_week.png",bbox_inches="tight"); plt.close(fig)
print("fig02 done")

# ---------- FIG 3: one day zoomed, with state shading ----------
t0d=t0+4*86400
j0,j1=np.searchsorted(t,t0d),np.searchsorted(t,t0d+86400)
fig,ax=plt.subplots(6,1,figsize=(12.5,9.4),sharex=True)
ax[0].plot(t[j0:j1],ch[1][j0:j1],lw=0.7,color="#111")
ax[0].set_title("AGGREGATE  —  can you tell what is on?",loc="left",fontsize=9.5,fontweight="bold")
ax[0].set_ylabel("W"); ax[0].set_ylim(0,np.percentile(ch[1][j0:j1],99.95)*1.15)
for k,c in enumerate([2,3,4,5,6]):
    a=ax[k+1]; p=ch[c][j0:j1]; st=(p>TH)
    a.fill_between(t[j0:j1],0,p,color=COL[c],lw=0,alpha=0.8)
    # shade ON intervals
    d=np.diff(st.astype(np.int8)); on=np.flatnonzero(d==1)+1; off=np.flatnonzero(d==-1)+1
    if st[0]: on=np.r_[0,on]
    if st[-1] and len(on)>len(off): off=np.r_[off,len(st)]
    for s_,e_ in zip(on,off): a.axvspan(t[j0:j1][s_],t[j0:j1][min(e_,len(st)-1)],color=COL[c],alpha=0.12,lw=0)
    a.set_ylabel("W"); a.set_title("GROUND TRUTH  —  "+NAME[c]+"   (ON "+f"{100*st.mean():.1f}"+"% of the day)",loc="left",fontsize=8.6,fontweight="bold",color=COL[c])
    a.set_ylim(0,max(60,np.percentile(p,99.5)*1.25))
ax[-1].set_xlabel("time")
import datetime as dt
fig.suptitle("Figure 3 — One day, unrolled: the aggregate is the sum, and the sum is what hides the parts",fontsize=12,fontweight="bold",y=0.997)
fig.text(0.5,0.004,"UK-DALE, 24 h at 6 s. Shaded bands mark ON intervals. Notice the washing machine: long multi-stage cycles, exactly the kind of load a single step size cannot describe.",
         ha="center",fontsize=7.8,color="#555")
fig.tight_layout(rect=[0,0.012,1,0.985]); fig.savefig(FIG+"/fig03_one_day_zoom.png",bbox_inches="tight"); plt.close(fig)
print("fig03 done")

# ---------- FIG 4: the event / dP view ----------
fig,ax=plt.subplots(2,2,figsize=(12.5,7.6))
# (a) zoom on a kettle event
p=ch[1]; d=np.abs(np.diff(p)); c=4
st=(ch[c]>TH); idx=np.flatnonzero(np.diff(st.astype(np.int8))==1)
k=idx[len(idx)//2]
w0,w1=max(0,k-150),min(len(p),k+250)
ax[0,0].plot(t[w0:w1]-t[k],p[w0:w1],color="#111",lw=1.1,label="aggregate")
ax[0,0].plot(t[w0:w1]-t[k],ch[c][w0:w1],color=COL[c],lw=1.1,label="kettle (truth)")
ax[0,0].axvline(0,color="#0a0",ls="--",lw=1)
ax[0,0].annotate("the step\nyou must detect",xy=(0,p[k]),xytext=(90,p[k]*0.55),
                 arrowprops=dict(arrowstyle="->",color="#0a0"),fontsize=8,color="#080")
ax[0,0].set_title("(a) what an 'event' looks like",loc="left",fontsize=9.5,fontweight="bold")
ax[0,0].set_xlabel("seconds around the event"); ax[0,0].set_ylabel("W"); ax[0,0].legend(fontsize=8)
# (b) histogram of aggregate |dP|
dd=np.abs(np.diff(p))
ax[0,1].hist(dd[dd<600],bins=120,color="#555")
ax[0,1].axvline(30,color="red",ls="--",lw=1.2); ax[0,1].text(34,ax[0,1].get_ylim()[1]*0.85,"30 VA\nShelly floor",color="red",fontsize=8)
ax[0,1].set_yscale("log")
ax[0,1].set_title("(b) every step the meter takes, 75 days",loc="left",fontsize=9.5,fontweight="bold")
ax[0,1].set_xlabel("|change in aggregate power| (W)"); ax[0,1].set_ylabel("count (log)")
# (c) per-appliance step distributions - the confusion
for c in [2,3,4,5,6]:
    st=(ch[c]>TH); ix=np.flatnonzero(np.diff(st.astype(np.int8))!=0)
    s=np.abs(np.diff(ch[c])[ix])
    if len(s)>12: ax[1,0].hist(s,bins=np.logspace(0.5,4,45),histtype="step",lw=1.5,color=COL[c],label=NAME[c])
ax[1,0].set_xscale("log")
ax[1,0].axvspan(0,30,color="red",alpha=0.10)
ax[1,0].set_title("(c) step sizes overlap: this is the whole problem",loc="left",fontsize=9.5,fontweight="bold")
ax[1,0].set_xlabel("size of the step this appliance makes (W)"); ax[1,0].set_ylabel("count"); ax[1,0].legend(fontsize=8)
# (d) simultaneity
nc=sum((ch[c]>TH).astype(int) for c in [2,3,4,5,6])
import collections
cnt=collections.Counter(nc.tolist()); tot=len(nc)
ks=sorted(cnt); vals=[100*cnt[k]/tot for k in ks]
bars=ax[1,1].bar([str(k) for k in ks],vals,color=["#4c72b0","#55a868","#c44e52","#8172b3","#937860"][:len(ks)])
for kk,vv in zip(ks,vals): ax[1,1].text(str(kk),vv+0.8,f"{vv:.1f}%",ha="center",fontsize=8.5)
ax[1,1].set_title("(d) how often appliances overlap",loc="left",fontsize=9.5,fontweight="bold")
ax[1,1].set_xlabel("number of monitored appliances ON at once"); ax[1,1].set_ylabel("% of time")
ax[1,1].text(0.98,0.80,"2 or more ON: "+f"{sum(v for k,v in cnt.items() if k>=2)*100/tot:.1f}"+"% of the time",
             transform=ax[1,1].transAxes,ha="right",fontsize=8.6,color="#c44e52",fontweight="bold")
fig.suptitle("Figure 4 — Reading the data the way an algorithm does: steps, not shapes",fontsize=12,fontweight="bold",y=0.995)
fig.tight_layout(rect=[0,0,1,0.975]); fig.savefig(FIG+"/fig04_event_view.png",bbox_inches="tight"); plt.close(fig)
print("fig04 done")
