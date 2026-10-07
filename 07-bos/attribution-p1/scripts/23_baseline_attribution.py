"""Фаза 2A, шаг 4: (A) базовая линия исходов, (B) атрибуция по деривативам по ПРЕДРЕГИСТРИРОВАННЫМ правилам (out/phase2a/PREREG.md)."""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings("ignore")
from scipy.stats import rankdata
Q="/Users/arefevoleg/bot_project_v2/LAB_attrib_p1/out/phase2a"; rng=np.random.default_rng(20261007)
X=pd.read_csv(Q+"/events_full.csv",parse_dates=["T"]); U=pd.read_csv(Q+"/unconditional_hours.csv")
HZ=[1,4,12,24,48,72]
# ---------- (A) база
rows=[]
for fam in ["1H_start","4H_start","TRANSITION","1H_end","4H_end","ALIGN_LOST","ALIGN_RESTORED"]:
    for dlab,mask in (("BULL",X.s>0),("BEAR",X.s<0),("pooled",X.s!=0)):
        x=X[(X.family==fam)&mask]
        for h in HZ:
            r=x[f"R{h}"].dropna()
            if len(r)==0: continue
            base_med=np.nanmedian(np.where(x.loc[r.index,"s"]>0, U[U.s==1][f"R{h}"].median(), U[U.s==-1][f"R{h}"].median()))
            rows.append({"family":fam,"dir":dlab,"h":h,"N":len(r),"clusters":x.loc[r.index,"cluster"].nunique(),"median_R_%":r.median()*100,"mean_R_%":r.mean()*100,
              "q25_%":r.quantile(.25)*100,"q75_%":r.quantile(.75)*100,"cont_%":(r>0).mean()*100,"rev_%":(r<0).mean()*100,"zero_n":int((r==0).sum()),
              "median_MFE_%":x.loc[r.index,f"MFE{h}"].median()*100,"median_MAE_%":x.loc[r.index,f"MAE{h}"].median()*100,"drift_median_%":base_med*100,"excess_median_%":(r.median()-base_med)*100})
B=pd.DataFrame(rows); B.to_csv(Q+"/A_baseline_outcomes.csv",index=False)
# KM длительности эпизодов
def km(d,cens):
    d=np.array(d,float); c=np.array(cens,bool); order=np.argsort(d); d=d[order]; ev=~c[order]; S=1.0; n=len(d); out=[]
    for i,(t,e) in enumerate(zip(d,ev)):
        if e: S*=1-1/(n-i); out.append((t,S))
    med=next((t for t,s in out if s<=0.5),np.nan); return med,len(d),int(ev.sum())
EP=pd.read_csv(Q+"/../episodes.csv",parse_dates=["first_seen_close","last_active_close"]); EP=EP[EP.in_win]
kmrows=[]
for tf,bh in (("1h",1),("4h",4)):
    e=EP[EP.tf==tf]; dur=((e.last_active_close-e.first_seen_close).dt.total_seconds()/3600+bh).values
    m,n,ne=km(dur,~e.ended_observed.values); kmrows.append({"tf":tf,"N":n,"завершено":ne,"цензурировано":n-ne,"медиана_KM_ч":m,"медиана_наблюд_ч":float(np.median(dur))})
pd.DataFrame(kmrows).to_csv(Q+"/A_km_durations.csv",index=False)
# ---------- (B) атрибуция
FEATS={"dOI_1h":"ΔOI 1ч","dOI_4h":"ΔOI 4ч","dOI_12h":"ΔOI 12ч","dOI_24h":"ΔOI 24ч","fa_T":"funding (×s) в T","df_4h":"Δfunding 4ч","df_24h":"Δfunding 24ч",
 "liq_ia_1h":"liq imbalance (×s) 1ч","liq_ia_4h":"liq imbalance (×s) 4ч","liq_ia_12h":"liq imbalance (×s) 12ч","liq_total_12h":"liq total 12ч","gm_Aa":"gamma асимметрия (×s)","gm_top_up_dist":"gamma: расст. до страйка-макс. выше, %","gm_top_dn_dist":"gamma: расст. до страйка-макс. ниже, %","tp_fa_4h":"tape flow (×s) 4ч","tp_fa_12h":"tape flow (×s) 12ч","tp_iv_12h":"tape IV 12ч"}
PRIM_F=["dOI_24h","fa_T","liq_ia_12h","gm_Aa","tp_fa_12h"]; PRIM_O=["R24","MAE24"]
def spear(x,y):
    rx,ry=rankdata(x),rankdata(y); return np.corrcoef(rx,ry)[0,1]
def perm_p(x,y,n=10000):
    rx,ry=rankdata(x),rankdata(y); obs=np.corrcoef(rx,ry)[0,1]
    ps=np.array([np.corrcoef(rx,rng.permutation(ry))[0,1] for _ in range(n)]); return (np.sum(np.abs(ps)>=abs(obs)-1e-12)+1)/(n+1)
def test(d,f,o):
    z=d[[f,o,"abs_ret_24h_before","cluster","s"]].dropna(subset=[f,o]); n=len(z)
    res={"n":n,"clusters":z.cluster.nunique(),"rho":np.nan,"p_perm":np.nan,"rho_vol":np.nan,"sign_c1":np.nan,"sign_c2":np.nan,"n_c1":0,"n_c2":0,"rho_bull":np.nan,"rho_bear":np.nan,"n_bull":int((z.s>0).sum()),"n_bear":int((z.s<0).sum())}
    if n<5 or z[f].nunique()<3: return res
    res["rho"]=spear(z[f],z[o]); res["p_perm"]=perm_p(z[f].values,z[o].values)
    zv=z.dropna(subset=["abs_ret_24h_before"]); res["rho_vol"]=spear(zv.abs_ret_24h_before,zv[o]) if len(zv)>=5 else np.nan
    for k,c in (("c1","1D#2026-08-19 BULL"),("c2","1D#2026-09-18 BULL")):
        zc=z[z.cluster==c]; res[f"n_{k}"]=len(zc)
        if len(zc)>=4 and zc[f].nunique()>=3: res[f"sign_{k}"]=np.sign(spear(zc[f],zc[o]))
    for k,m in (("bull",z.s>0),("bear",z.s<0)):
        zz=z[m]
        if len(zz)>=5 and zz[f].nunique()>=3: res[f"rho_{k}"]=spear(zz[f],zz[o])
    return res
def status(r,primary):
    if r["n"]<8 or r["clusters"]<2 or np.isnan(r["rho"]): return "INSUFFICIENT DATA"
    consistent = (not np.isnan(r["sign_c1"])) and (not np.isnan(r["sign_c2"])) and r["sign_c1"]==r["sign_c2"]==np.sign(r["rho"])
    cand = r["p_perm"]<0.05 and consistent and abs(r["rho"])>abs(r["rho_vol"] if not np.isnan(r["rho_vol"]) else 0) and r["n"]>=10
    if cand and primary: return "INTERESTING CANDIDATE"
    if r["p_perm"]<0.20 or abs(r["rho"])>=0.20: return "WEAK / INCONSISTENT"
    return "NO EFFECT"
res=[]
F1=X[X.family=="1H_start"]
for f in PRIM_F:
    for o in PRIM_O:
        r=test(F1,f,o); r.update({"set":"F1 1H_start","feature":f,"outcome":o,"primary":True}); res.append(r)
P=pd.DataFrame(res); P["p_holm"]=np.nan
order=P.p_perm.sort_values().index; m=len(P); prev=0
for rank,i in enumerate(order):
    if np.isnan(P.loc[i,"p_perm"]): continue
    adj=min(1,(m-rank)*P.loc[i,"p_perm"]); prev=max(prev,adj); P.loc[i,"p_holm"]=prev
P["status"]=[status(r,True) for _,r in P.iterrows()]
# вторичные
sec=[]
for setname,d in (("F1 1H_start",F1),("F3 TRANSITION",X[X.family=="TRANSITION"]),("F2 4H_start",X[X.family=="4H_start"]),("F1 1H_end",X[X.family=="1H_end"])):
    for f in FEATS:
        for o in ["R4","R12","R24","MAE24"]:
            if setname=="F1 1H_start" and f in PRIM_F and o in PRIM_O: continue
            r=test(d,f,o); r.update({"set":setname,"feature":f,"outcome":o,"primary":False}); sec.append(r)
S=pd.DataFrame(sec); S["status"]=[status(r,False) for _,r in S.iterrows()]
S["naive_crit"]=[(r["p_perm"]<0.05 and r["n"]>=10) if not np.isnan(r["p_perm"]) else False for _,r in S.iterrows()]
A=pd.concat([P,S]); A["feature_name"]=A.feature.map(FEATS); A.to_csv(Q+"/B_attribution_all.csv",index=False)
print("=== (A) база, медианы R_h (%), direction-normalized pooled ==="); print(B[B["dir"]=="pooled"].pivot(index="family",columns="h",values="median_R_%").round(3).to_string())
print("\nN по горизонтам:"); print(B[B["dir"]=="pooled"].pivot(index="family",columns="h",values="N").to_string())
print("\ncont%:"); print(B[B["dir"]=="pooled"].pivot(index="family",columns="h",values="cont_%").round(0).to_string())
print("\nKM:"); print(pd.DataFrame(kmrows).to_string(index=False))
print("\n=== (B) первичное семейство (10 тестов) ==="); print(P[["feature","outcome","n","clusters","rho","p_perm","p_holm","rho_vol","sign_c1","sign_c2","n_c1","n_c2","status"]].round(3).to_string(index=False))
print("\nвторичных тестов:",len(S),"| статусы:",S.status.value_counts().to_dict(),"| с наивным p<0.05 и n>=10:",int(S.naive_crit.sum()),"| ожидаемо по случайности ~",round(0.05*len(S[S.status!="INSUFFICIENT DATA"]),1))
print("\nвторичные с наивным p<0.05 (n>=10):"); print(S[S.naive_crit][["set","feature","outcome","n","rho","p_perm","rho_vol","sign_c1","sign_c2","status"]].round(3).to_string(index=False))
