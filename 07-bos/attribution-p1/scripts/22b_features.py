"""Фаза 2A, шаг 3: деривативные признаки на моменты событий. Только timestamp <= T. Устаревшее/невалидное -> NaN (MISSING), без forward-fill."""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings("ignore")
P="/Users/arefevoleg/bot_project_v2"; O=P+"/LAB_attrib_p1/out"; Q=O+"/phase2a"
def ts(s): r=pd.to_datetime(s,utc=True,format="ISO8601").dt.tz_localize(None); assert r.notna().all() and (r.dt.year==2026).all(); return r
E=pd.read_csv(Q+"/events.csv",parse_dates=["T"])
ns=lambda t: np.datetime64(t,"ns").astype("int64")
def asof(times,vals,T,limit_s):
    j=np.searchsorted(times,ns(T),side="right")-1
    if j<0: return np.nan
    return vals[j] if (ns(T)-times[j])/1e9<=limit_s else np.nan
# OI
oi=pd.read_csv(P+"/oi_raw.csv"); oi["t"]=ts(oi.recv_ts_utc); oi=oi.sort_values("t"); oi_t=oi.t.values.astype("datetime64[ns]").astype("int64"); oi_v=oi.open_interest.values
# funding
fu=pd.read_csv(P+"/funding_markprice_raw.csv",usecols=["recv_ts_utc","funding_rate"]); fu["t"]=ts(fu.recv_ts_utc); fu=fu.sort_values("t"); fu_t=fu.t.values.astype("datetime64[ns]").astype("int64"); fu_v=fu.funding_rate.values
# liq
lq=pd.read_csv(P+"/liquidations_raw.csv",usecols=["recv_ts_utc","liquidation_side","notional_usd"]); lq["t"]=ts(lq.recv_ts_utc); lq=lq.sort_values("t")
M=pd.read_csv(O+"/liq_invalid_union_v2.csv",parse_dates=["from","to"]); LQ0=pd.Timestamp("2026-08-29 11:28:12")
def liq_cov(a,b):
    if a<LQ0: return 0.0
    bad=sum(max(0,(min(b,e)-max(a,s)).total_seconds()) for s,e in zip(M["from"],M["to"])); return 1-bad/(b-a).total_seconds()
# gamma
GS=pd.read_csv(Q+"/gamma_snapshot_features.csv",parse_dates=["ts"]); gs_t=GS.ts.values.astype("datetime64[ns]").astype("int64"); GAMMA_END=pd.Timestamp("2026-10-02 10:10")
# tape
tp=pd.read_csv(P+"/deribit_option_trades_raw.csv",usecols=["timestamp_ms","instrument_name","direction","amount","index_price","iv","block_trade_id","combo_id"])
tp["t"]=pd.to_datetime(tp.timestamp_ms,unit="ms"); tp=tp.sort_values("t"); tp["cp"]=tp.instrument_name.str[-1]; tp["usd"]=tp.amount*tp.index_price
tp["sgn"]=np.where(tp.direction=="buy",1,-1); tp["net"]=tp.usd*tp.sgn; tp_t=tp.t.values.astype("datetime64[ns]").astype("int64")
TB=(pd.Timestamp("2026-10-02 00:00"),pd.Timestamp("2026-10-06 23:05")); TAPE0=pd.Timestamp("2026-08-28 21:27")
rows=[]
for e in E.itertuples():
    T,s=e.T,e.s; r={"ev_id":e.ev_id}
    o0=asof(oi_t,oi_v,T,900); r["oi_T"]=o0
    for w in (1,4,12,24):
        ow=asof(oi_t,oi_v,T-pd.Timedelta(hours=w),900); r[f"dOI_{w}h"]=o0/ow-1 if (o0==o0 and ow==ow) else np.nan
    f0=asof(fu_t,fu_v,T,60); r["f_T"]=f0; r["fa_T"]=s*f0 if f0==f0 else np.nan
    for w in (4,24):
        fw=asof(fu_t,fu_v,T-pd.Timedelta(hours=w),60); r[f"df_{w}h"]=f0-fw if (f0==f0 and fw==fw) else np.nan
    for w in (1,4,12):
        a=T-pd.Timedelta(hours=w); ok=liq_cov(a,T)>=0.9
        if ok:
            x=lq[(lq.t>a)&(lq.t<=T)]; L=x[x.liquidation_side=="LONG_LIQUIDATION"].notional_usd.sum(); S=x[x.liquidation_side=="SHORT_LIQUIDATION"].notional_usd.sum(); tot=L+S
            r.update({f"liq_long_{w}h":L,f"liq_short_{w}h":S,f"liq_total_{w}h":tot,f"liq_imb_{w}h":(S-L)/tot if tot>0 else np.nan}); r[f"liq_ia_{w}h"]=s*r[f"liq_imb_{w}h"]
        else: r.update({f"liq_long_{w}h":np.nan,f"liq_short_{w}h":np.nan,f"liq_total_{w}h":np.nan,f"liq_imb_{w}h":np.nan,f"liq_ia_{w}h":np.nan})
    j=np.searchsorted(gs_t,ns(T),side="right")-1
    if j>=0 and (ns(T)-gs_t[j])/1e9<=1200 and GS.ts.iloc[j]<=GAMMA_END:
        g=GS.iloc[j]; r.update({"gm_A":g.A,"gm_Aa":s*g.A,"gm_G_up":g.G_up,"gm_G_dn":g.G_dn,"gm_top_up_dist":g.top_up_dist_pct,"gm_top_dn_dist":g.top_dn_dist_pct,"gm_top_up_share":g.top_up_share,"gm_top_dn_share":g.top_dn_share,"gm_spot":g.spot})
    for w in (4,12):
        a=T-pd.Timedelta(hours=w)
        if a<TAPE0 or (a<=TB[1] and T>=TB[0]): r.update({f"tp_flow_{w}h":np.nan,f"tp_fa_{w}h":np.nan,f"tp_iv_{w}h":np.nan,f"tp_n_{w}h":np.nan,f"tp_blk_{w}h":np.nan,f"tp_cnet_{w}h":np.nan,f"tp_pnet_{w}h":np.nan,f"tp_abs_{w}h":np.nan}); continue
        lo=np.searchsorted(tp_t,ns(a),side="right"); hi=np.searchsorted(tp_t,ns(T),side="right"); x=tp.iloc[lo:hi]
        if len(x)==0: r.update({f"tp_n_{w}h":0}); continue
        cn=x[x.cp=="C"].net.sum(); pn=x[x.cp=="P"].net.sum(); ab=x.usd.sum(); xi=x[(x.iv>0)]
        r[f"tp_cnet_{w}h"]=cn; r[f"tp_pnet_{w}h"]=pn; r[f"tp_abs_{w}h"]=ab; r[f"tp_flow_{w}h"]=(cn-pn)/ab if ab>0 else np.nan; r[f"tp_fa_{w}h"]=s*r[f"tp_flow_{w}h"]
        r[f"tp_iv_{w}h"]=np.average(xi.iv,weights=xi.usd) if len(xi) and xi.usd.sum()>0 else np.nan; r[f"tp_n_{w}h"]=len(x); r[f"tp_blk_{w}h"]=int(x.block_trade_id.notna().sum()+x.combo_id.notna().sum())
    rows.append(r)
F=pd.DataFrame(rows); X=pd.read_csv(Q+"/events_outcomes.csv",parse_dates=["T"]).merge(F,on="ev_id"); X.to_csv(Q+"/events_full.csv",index=False)
print("доступность признаков (не NaN) по семействам:")
cols=["dOI_24h","fa_T","liq_ia_12h","gm_Aa","tp_fa_12h"]
print(X.groupby("family")[cols].count().assign(N=X.groupby("family").size()).to_string())
