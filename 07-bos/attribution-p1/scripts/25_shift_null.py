"""Диагностика автокорреляции: нулевое распределение ρ через случайный СДВИГ ряда признака по времени относительно событий
(сохраняет автокорреляцию признака). Применяется одинаково к кандидату из первичного семейства и к самому сильному вторичному результату.
Ничего не оптимизируется; сдвиги ≥48 ч, оборачиваются внутри валидного сегмента данных."""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings("ignore")
from scipy.stats import spearmanr
P="/Users/arefevoleg/bot_project_v2"; Q=P+"/LAB_attrib_p1/out/phase2a"; rng=np.random.default_rng(7)
X=pd.read_csv(Q+"/events_full.csv",parse_dates=["T"])
ns=lambda t: np.datetime64(t,"ns").astype("int64")
# --- gamma
GS=pd.read_csv(Q+"/gamma_snapshot_features.csv",parse_dates=["ts"]); GS=GS[GS.ts<=pd.Timestamp("2026-10-02 10:10")].sort_values("ts")
g_t=GS.ts.values.astype("datetime64[ns]").astype("int64"); g_A=GS.A.values; G0,G1=GS.ts.min(),GS.ts.max()
def gamma_A(T):
    j=np.searchsorted(g_t,ns(T),side="right")-1
    return g_A[j] if j>=0 and (ns(T)-g_t[j])/1e9<=1200 else np.nan
# --- tape (кумулятивные суммы)
tp=pd.read_csv(P+"/deribit_option_trades_raw.csv",usecols=["timestamp_ms","instrument_name","direction","amount","index_price"]); tp["t"]=pd.to_datetime(tp.timestamp_ms,unit="ms"); tp=tp.sort_values("t")
usd=(tp.amount*tp.index_price).values; sg=np.where(tp.direction=="buy",1,-1); cp=np.where(tp.instrument_name.str[-1]=="C",1,-1)
t_ns=tp.t.values.astype("datetime64[ns]").astype("int64"); cn=np.cumsum(np.where(cp==1,usd*sg,0)); pn=np.cumsum(np.where(cp==-1,usd*sg,0)); ab=np.cumsum(usd)
W=12*3600*10**9
def tape_flow(T):
    hi=np.searchsorted(t_ns,ns(T),side="right"); lo=np.searchsorted(t_ns,ns(T)-W,side="right")
    if hi<=lo: return np.nan
    a=ab[hi-1]-(ab[lo-1] if lo>0 else 0)
    if a<=0: return np.nan
    c=cn[hi-1]-(cn[lo-1] if lo>0 else 0); p=pn[hi-1]-(pn[lo-1] if lo>0 else 0); return (c-p)/a
TP0,TP1=pd.Timestamp("2026-08-29 09:30"),pd.Timestamp("2026-10-01 23:59")
def shift_test(d,fn,seg0,seg1,outcome,label,n=3000):
    d=d.dropna(subset=[outcome]).copy(); d=d[(d['T']>=seg0)&(d['T']<=seg1)].copy(); span=(seg1-seg0).total_seconds()   # события вне валидного сегмента признака исключаются
    def feat(shift_s):
        v=[]
        for T,s in zip(d["T"],d.s):
            T2=seg0+pd.Timedelta(seconds=((T-seg0).total_seconds()+shift_s)%span); f=fn(T2); v.append(s*f if f==f else np.nan)
        return np.array(v)
    obs_f=np.array([ (s*fn(T) if fn(T)==fn(T) else np.nan) for T,s in zip(d["T"],d.s)]); ok=~np.isnan(obs_f)
    if ok.sum()<8: print(label,"n<8"); return
    obs=spearmanr(obs_f[ok],d[outcome].values[ok])[0]; null=[]
    for _ in range(n):
        sh=rng.uniform(48*3600,span-48*3600); f=feat(sh); m=~np.isnan(f)
        if m.sum()>=8: null.append(spearmanr(f[m],d[outcome].values[m])[0])
    null=np.array(null); p=(np.sum(np.abs(null)>=abs(obs))+1)/(len(null)+1)
    print(f"{label}: n={int(ok.sum())} ρ_набл={obs:+.3f} | сдвиговый нуль: sd={null.std():.3f}, 95%|ρ|≤{np.quantile(np.abs(null),.95):.3f} | p_сдвиг={p:.3f} (сдвигов {len(null)})")
F1=X[X.family=="1H_start"]; F3=X[X.family=="TRANSITION"]
shift_test(F1,tape_flow,TP0,TP1,"MAE24","[первичный кандидат] F1 tape Fa_12h → MAE24")
shift_test(F3,tape_flow,TP0,TP1,"MAE24","[контроль] F3 tape Fa_12h → MAE24")
shift_test(F3,gamma_A,G0,G1,"MAE24","[вторичный] F3 gamma Aa → MAE24")
shift_test(F1,gamma_A,G0,G1,"MAE24","[первичный] F1 gamma Aa → MAE24")
# прореживание F3 (≥24 ч между событиями) — эффективное число независимых окон MAE24
t=F3.sort_values("T"); keep=[]; last=None
for _,r in t.iterrows():
    if last is None or (r["T"]-last).total_seconds()>=24*3600: keep.append(r.ev_id); last=r["T"]
th=F3[F3.ev_id.isin(keep)].dropna(subset=["gm_Aa","MAE24"]); print(f"\nF3 прореженные (≥24ч): {len(keep)} событий; с gamma и MAE24: {len(th)}; ρ(gm_Aa,MAE24)={spearmanr(th.gm_Aa,th.MAE24)[0]:+.3f}")
for lab,m in (("до 16.09",F3["T"]<pd.Timestamp("2026-09-16")),("после 16.09",F3["T"]>=pd.Timestamp("2026-09-16"))):
    z=F3[m].dropna(subset=["gm_Aa","MAE24"]); print(f"F3 {lab}: n={len(z)} ρ={spearmanr(z.gm_Aa,z.MAE24)[0]:+.3f}" if len(z)>=5 else f"F3 {lab}: n<5")
print("состав F3 по s:",F3.s.value_counts().to_dict(),"| gm_Aa vs gm_A у s=+1 совпадают:", bool((F3[F3.s==1].gm_Aa==F3[F3.s==1].gm_A).all()))
