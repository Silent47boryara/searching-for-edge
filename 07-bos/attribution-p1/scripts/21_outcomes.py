"""Фаза 2A, шаг 2: исходы по пути цены 1H (R_h, MFE_h, MAE_h) + безусловный контроль (дрейф)."""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings("ignore")
O="/Users/arefevoleg/bot_project_v2/LAB_attrib_p1"; Q=O+"/out/phase2a"
k=pd.read_csv(O+"/raw/BTCUSDT_1h_binance_raw.csv"); k["tc"]=pd.to_datetime(k.open_time_ms,unit="ms")+pd.Timedelta(hours=1)
k=k.reset_index(drop=True); idx={t:i for i,t in enumerate(k.tc)}; C=k.Close.values; H=k.High.values; L=k.Low.values
HZ=[1,4,12,24,48,72]
def path(i,s,h):
    if i is None or i+h>=len(k): return (np.nan,)*3
    P=C[i]; j=slice(i+1,i+h+1); r=s*(C[i+h]/P-1)
    if s==1: fav=H[j].max()/P-1; adv=L[j].min()/P-1
    else: fav=1-L[j].min()/P; adv=-(H[j].max()/P-1)
    return r,fav,adv
E=pd.read_csv(Q+"/events.csv",parse_dates=["T"]); rows=[]
for e in E.itertuples():
    i=idx.get(e.T)
    r={"ev_id":e.ev_id,"P_T":C[i] if i is not None else np.nan}
    # предшествующая |доходность| за 24ч (контроль волатильностью), по закрытиям ≤T
    r["abs_ret_24h_before"]=abs(C[i]/C[i-24]-1) if i is not None and i>=24 else np.nan
    for h in HZ:
        a,b,c=path(i,e.s,h); r[f"R{h}"]=a; r[f"MFE{h}"]=b; r[f"MAE{h}"]=c
    rows.append(r)
Out=pd.DataFrame(rows); X=E.merge(Out,on="ev_id"); X.to_csv(Q+"/events_outcomes.csv",index=False)
miss=X[X.P_T.isna()]; print("событий без привязки к бару:",len(miss))
print("валидные наблюдения по горизонтам (R_h не NaN):"); print(X.groupby("family")[[f"R{h}" for h in HZ]].count().to_string())
# безусловный контроль: все часы окна, s=+1 и s=-1
ctl=[]
for i in range(len(k)):
    if k.tc[i]<pd.Timestamp("2026-08-29 12:00"): continue
    for s in (1,-1):
        d={"s":s}
        for h in HZ: d[f"R{h}"],d[f"MFE{h}"],d[f"MAE{h}"]=path(i,s,h)
        d["t"]=k.tc[i]; ctl.append(d)
Ct=pd.DataFrame(ctl); Ct.to_csv(Q+"/unconditional_hours.csv",index=False)
print("\nбезусловный дрейф: медиана R_h, %  (s=+1 / s=-1)")
for h in HZ: print(f"h={h:>2}ч: {Ct[Ct.s==1][f'R{h}'].median()*100:+.3f} / {Ct[Ct.s==-1][f'R{h}'].median()*100:+.3f}   N={Ct[Ct.s==1][f'R{h}'].count()}")
