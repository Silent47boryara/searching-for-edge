from pathlib import Path
import pandas as pd,numpy as np
from scipy.stats import spearmanr
O=Path(__file__).parent;P=Path('/Users/arefevoleg/bot_project_v2');Q=P/'LAB_attrib_p1/out/phase2a'
E=pd.read_csv(O/'events.csv');E['T']=pd.to_datetime(E['T'],utc=True)
old=pd.read_csv(Q/'events_full.csv');old['T']=pd.to_datetime(old['T'],utc=True)
for tf,fam in [('1h','1H_start'),('4h','4H_start')]:
    a=E[(E.tf==tf)&(E.model=='original')];b=old[old.family==fam];sa=set(zip(a['T'],a.s));sb=set(zip(b['T'],b.s));print('ORIGINAL starts vs Phase2a',tf,len(sa),len(sb),'only new',sa-sb,'only old',sb-sa)
# fixed candidate tape; original data/masks, no new feature search
raw=pd.read_csv(P/'LAB_attrib_p1/raw/BTCUSDT_1h_binance_raw.csv');raw['T']=pd.to_datetime(raw.open_time_ms,unit='ms',utc=True)+pd.Timedelta(hours=1);raw=raw.set_index('T')
tp=pd.read_csv(P/'deribit_option_trades_raw.csv',usecols=['timestamp_ms','instrument_name','direction','amount','index_price']);tp=tp.sort_values('timestamp_ms');nt=tp.timestamp_ms.to_numpy();usd=(tp.amount*tp.index_price).to_numpy();net=usd*np.where(tp.direction=='buy',1,-1)*np.where(tp.instrument_name.str[-1]=='C',1,-1);cs=np.r_[0,np.cumsum(net)];ca=np.r_[0,np.cumsum(usd)]
def mae(T,s):
    z=raw[(raw.index>T)&(raw.index<=T+pd.Timedelta(hours=24))]
    if len(z)!=24 or T not in raw.index:return np.nan
    p=raw.loc[T,'Close'];return min(0,(z.Low.min()/p-1)*100) if s==1 else min(0,(1-z.High.max()/p)*100)
def tape(T,s):
    a=T-pd.Timedelta(hours=12)
    if a<pd.Timestamp('2026-08-28 21:27',tz='UTC') or (a<=pd.Timestamp('2026-10-06 23:05',tz='UTC') and T>=pd.Timestamp('2026-10-02',tz='UTC')):return np.nan
    lo=np.searchsorted(nt,a.value//10**6,side='right');hi=np.searchsorted(nt,T.value//10**6,side='right');den=ca[hi]-ca[lo];return s*(cs[hi]-cs[lo])/den if den>0 else np.nan
rows=[]
for e in E[E.tf=='1h'].itertuples():rows.append({'model':e.model,'family':'1H_start','T':e.T,'s':e.s,'feature':tape(e.T,e.s),'MAE24':mae(e.T,e.s)})
GS=pd.read_csv(Q/'gamma_snapshot_features.csv');GS['T']=pd.to_datetime(GS.ts,utc=True);gtime=GS['T'].astype('int64').to_numpy()
R={tf:pd.read_csv(O/f'replay_{tf}.csv') for tf in ['1h','4h','1d']}
for tf in R:R[tf]['T']=pd.to_datetime(R[tf]['T'],utc=True)
transition_counts=[]
for model in ['original','lag_fixed','fallback_contract']:
    g=R['1h'][['T',model]].rename(columns={model:'h1'})
    for tf,label in [('4h','h4'),('1d','d1')]:g=pd.merge_asof(g,R[tf][['T',model]].rename(columns={model:label}),on='T',direction='backward')
    g=g.dropna().copy();chg=g[['d1','h4','h1']].ne(g[['d1','h4','h1']].shift()).any(axis=1);z=g[chg&(g['T']>=pd.Timestamp('2026-08-29 11:28:12',tz='UTC'))&(g['T']<=pd.Timestamp('2026-10-07 09:00',tz='UTC'))]
    transition_counts.append({'model':model,'N':len(z)})
    for e in z.itertuples():
        s=int(e.d1 or e.h4 or e.h1)
        if not s:continue
        j=np.searchsorted(gtime,e.T.value,side='right')-1;feature=np.nan
        if j>=0 and e.T.value-gtime[j]<=1200*10**9 and GS['T'].iloc[j]<=pd.Timestamp('2026-10-02 10:10',tz='UTC'):feature=s*GS.A.iloc[j]
        rows.append({'model':model,'family':'TRANSITION','T':e.T,'s':s,'feature':feature,'MAE24':mae(e.T,s)})
C=pd.DataFrame(rows);C.to_csv(O/'fixed_collectors_cases.csv',index=False);res=[]
for (model,fam),q in C.groupby(['model','family']):
    q=q.dropna(subset=['feature','MAE24']);rho=spearmanr(q.feature,q.MAE24).statistic if len(q)>2 else np.nan
    res.append({'model':model,'family':fam,'valid_n':len(q),'rho':rho})
pd.DataFrame(res).to_csv(O/'fixed_collectors_summary.csv',index=False)
print('TRANSITION counts',transition_counts);print(pd.DataFrame(res).to_string(index=False))
# Exact agreement on reused original feature/outcome points, no claims of independent replication.
for fam,col in [('1H_start','tp_fa_12h'),('TRANSITION','gm_Aa')]:
    a=C[(C.model=='original')&(C.family==fam)];b=old[old.family==fam];z=a.merge(b,on=['T','s']);diff=(z.feature-z[col]).abs().max();md=(z.MAE24-100*z['MAE24_y']).abs().max() if 'MAE24_x' not in z else (z.MAE24_x-100*z.MAE24_y).abs().max()
    print('FROZEN CHECK',fam,'matched',len(z),'feature_maxdiff',diff,'MAE_maxdiff',md)
