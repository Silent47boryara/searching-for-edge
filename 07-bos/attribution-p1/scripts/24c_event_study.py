"""Фаза 2A, п.5: event study (−24…+24 ч вокруг T). Всё выровнено по направлению s. Показаны отдельные события (тонко) и медиана (толсто)."""
import pandas as pd, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt, warnings; warnings.filterwarnings("ignore")
P="/Users/arefevoleg/bot_project_v2"; O=P+"/LAB_attrib_p1/out"; Q=O+"/phase2a"
def ts(s): r=pd.to_datetime(s,utc=True,format="ISO8601").dt.tz_localize(None); assert r.notna().all(); return r
ns=lambda t: np.datetime64(t,"ns").astype("int64")
E=pd.read_csv(Q+"/events.csv",parse_dates=["T"])
k=pd.read_csv(P+"/LAB_attrib_p1/raw/BTCUSDT_1h_binance_raw.csv"); k["tc"]=pd.to_datetime(k.open_time_ms,unit="ms")+pd.Timedelta(hours=1); kidx={t:i for i,t in enumerate(k.tc)}; C=k.Close.values
oi=pd.read_csv(P+"/oi_raw.csv"); oi["t"]=ts(oi.recv_ts_utc); oi=oi.sort_values("t"); oi_t=oi.t.values.astype("datetime64[ns]").astype("int64"); oi_v=oi.open_interest.values
fu=pd.read_csv(P+"/funding_markprice_raw.csv",usecols=["recv_ts_utc","funding_rate"]); fu["t"]=ts(fu.recv_ts_utc); fu=fu.sort_values("t"); fu_t=fu.t.values.astype("datetime64[ns]").astype("int64"); fu_v=fu.funding_rate.values
lq=pd.read_csv(P+"/liquidations_raw.csv",usecols=["recv_ts_utc","liquidation_side","notional_usd"]); lq["t"]=ts(lq.recv_ts_utc); lq=lq.sort_values("t"); lq["sg"]=np.where(lq.liquidation_side=="SHORT_LIQUIDATION",1,-1)*lq.notional_usd
M=pd.read_csv(O+"/liq_invalid_union_v2.csv",parse_dates=["from","to"]); LQ0=pd.Timestamp("2026-08-29 11:28:12")
def lcov(a,b):
    if a<LQ0: return 0.0
    bad=sum(max(0,(min(b,e)-max(a,s)).total_seconds()) for s,e in zip(M["from"],M["to"])); return 1-bad/(b-a).total_seconds()
tp=pd.read_csv(P+"/deribit_option_trades_raw.csv",usecols=["timestamp_ms","instrument_name","direction","amount","index_price"]); tp["t"]=pd.to_datetime(tp.timestamp_ms,unit="ms"); tp=tp.sort_values("t")
tp["net"]=tp.amount*tp.index_price*np.where(tp.direction=="buy",1,-1)*np.where(tp.instrument_name.str[-1]=="C",1,-1)   # колы +, путы −
TB=(pd.Timestamp("2026-10-02 00:00"),pd.Timestamp("2026-10-06 23:05")); TP0=pd.Timestamp("2026-08-28 21:27")
def asof(times,vals,T,lim):
    j=np.searchsorted(times,ns(T),side="right")-1
    return vals[j] if j>=0 and (ns(T)-times[j])/1e9<=lim else np.nan
K=np.arange(-24,25)
def series(T,s):
    i=kidx.get(T); r={}
    r["price"]=np.array([s*(C[i+j]/C[i]-1)*100 if i is not None and 0<=i+j<len(C) else np.nan for j in K])
    o0=asof(oi_t,oi_v,T,900); r["oi"]=np.array([(asof(oi_t,oi_v,T+pd.Timedelta(hours=int(j)),900)/o0-1)*100 if o0==o0 else np.nan for j in K])
    f0=asof(fu_t,fu_v,T,60); r["fund"]=np.array([s*(asof(fu_t,fu_v,T+pd.Timedelta(hours=int(j)),60)-f0)*1e4 if f0==f0 else np.nan for j in K])
    L=[];Tn=[]
    for j in K:
        b=T+pd.Timedelta(hours=int(j)); a=b-pd.Timedelta(hours=1)
        if lcov(a,b)>=0.9: x=lq[(lq.t>a)&(lq.t<=b)]; L.append(s*x.sg.sum()/1e6)
        else: L.append(np.nan)
        if a<TP0 or (a<=TB[1] and b>=TB[0]): Tn.append(np.nan)
        else: x=tp[(tp.t>a)&(tp.t<=b)]; Tn.append(s*x.net.sum()/1e6)
    r["liq"]=np.array(L); r["tape"]=np.array(Tn); return r
fams=[("1H_start","Старт 1H-эпизода"),("1H_end","Конец 1H-эпизода"),("4H_start","Старт 4H-эпизода"),("4H_end","Конец 4H-эпизода (ACTIVE→NONE)"),("1H_start_against1D","Старт 1H против активного 1D"),("ALIGN_LOST","Потеря полного выравнивания"),("ALIGN_RESTORED","Восстановление полного выравнивания")]
titles={"price":"цена, % (по направлению)","oi":"OI, % к значению в T","fund":"funding, б.п. (по направлению, к T)","liq":"ликвидации по направлению: (шорты−лонги)·s, млн USD/ч","tape":"tape: чистый поток (колы−путы, покупки−продажи)·s, млн USD/ч"}
summ=[]
for key,name in fams:
    d=E[E.family==key] if key!="1H_start_against1D" else E[(E.family=="1H_start")&(E.against_1d==True)]
    R=[series(r["T"],r["s"]) for _,r in d.iterrows()]
    fig,ax=plt.subplots(5,1,figsize=(11,13),sharex=True)
    for a,v in zip(ax,["price","oi","fund","liq","tape"]):
        arr=np.vstack([x[v] for x in R]); 
        for row in arr: a.plot(K,row,color="grey",lw=.6,alpha=.6)
        med=np.nanmedian(arr,axis=0); n=(~np.isnan(arr)).sum(axis=0); a.plot(K,med,color="crimson",lw=2.2); a.axvline(0,color="k",ls="--",lw=.8); a.axhline(0,color="k",lw=.4)
        a.set_ylabel("")
        if v in ("liq","tape"):
            lim=np.nanpercentile(np.abs(arr),95)*1.5
            if lim==lim and lim>0: a.set_ylim(-lim,lim)
        a.set_title(f"{titles[v]} — событий с данными в T: {int(n[24])} из {len(R)}"+("; ось обрезана по 95-му перцентилю" if v in ("liq","tape") else ""),fontsize=8)
        for kk,m in zip(K,med): summ.append({"family":key,"layer":v,"k_h":int(kk),"median":m,"n":int(n[list(K).index(kk)])})
    ax[-1].set_xlabel("часы от момента T (закрытие бара/перехода)"); fig.suptitle(f"{name}: N={len(d)} событий, 1D-кластеров {d.cluster.nunique()}  [EXPLORATORY / INSUFFICIENT FOR CONFIRMATION]  красная — медиана",fontsize=10)
    fig.tight_layout(rect=[0,0,1,.97]); fig.savefig(f"{Q}/ES_{key}.png",dpi=90); plt.close(fig)
S=pd.DataFrame(summ); S.to_csv(Q+"/ES_medians.csv",index=False)
print("ключевые медианы (k=−12,0,+12,+24) по семействам и слоям:")
for key,_ in fams:
    x=S[S.family==key]; print(key, {v:[round(float(x[(x.layer==v)&(x.k_h==kk)]["median"].iloc[0]),3) if not np.isnan(x[(x.layer==v)&(x.k_h==kk)]["median"].iloc[0]) else None for kk in (-12,0,12,24)] for v in ["price","oi","fund","liq","tape"]})
