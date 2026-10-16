from pathlib import Path
import pandas as pd,numpy as np
def conf(y,p):return np.bincount((y.astype(int)+1)*3+p.astype(int)+1,minlength=9).reshape(3,3)
def scores(cm):
    diag=np.diag(cm);rec=diag/np.maximum(cm.sum(axis=1),1);prec=diag/np.maximum(cm.sum(axis=0),1);f=2*prec*rec/np.maximum(prec+rec,1e-20);present=cm.sum(axis=1)>0
    return float(rec[present].mean()),float(f[present].mean())
O=Path(__file__).parent;P=Path('/Users/arefevoleg/bot_project_v2');res=[];waveout=[]
for tf in ['1h','4h','1d']:
    r=pd.read_csv(O/f'replay_{tf}.csv');r['T']=pd.to_datetime(r['T'],utc=True);y=np.where(r.past12>1,1,np.where(r.past12<-1,-1,0));ema=np.where(r.close-r.ema20>.5*r.atr,1,np.where(r.close-r.ema20<-.5*r.atr,-1,0));held=ema[(np.arange(len(r))//24)*24]
    for model,p in [('original',r.original.to_numpy()),('lag_fixed',r.lag_fixed.to_numpy()),('ema20',ema),('ema20_hold24',held)]:
        res.append({'tf':tf,'model':model,'BA':scores(conf(y,p))[0],'switches_per_day':np.sum(p[1:]!=p[:-1])/((r['T'].max()-r['T'].min()).total_seconds()/86400)})
# waves use 1H closing prices only; extreme time is retrospective, available state evaluated by closed-hour T.
a=pd.read_csv(P/'BTCUSDT_1h_history_full.csv');a['t']=pd.to_datetime(a['Open time'],utc=True)+pd.Timedelta(hours=1)
b=pd.read_csv(P/'LAB_attrib_p1/raw/BTCUSDT_1h_binance_raw.csv');b['t']=pd.to_datetime(b.open_time_ms,unit='ms',utc=True)+pd.Timedelta(hours=1)
d=pd.concat([a[['t','Close']],b[['t','Close']]]).drop_duplicates('t',keep='last').sort_values('t').reset_index(drop=True)
# skip completed waves crossing unavailable source hour.
c=d.Close.to_numpy();t=d.t;mode=0;hi=lo=0;last=None;waves=[]
for i in range(1,len(d)):
    if mode==0:
        if c[i]>c[hi]:hi=i
        if c[i]<c[lo]:lo=i
        if c[i]>=c[lo]*1.08:mode=1;last=lo;hi=i
        elif c[i]<=c[hi]/1.08:mode=-1;last=hi;lo=i
    elif mode==1:
        if c[i]>c[hi]:hi=i
        if c[i]<=c[hi]/1.08:
            waves.append((last,hi,1));last=hi;mode=-1;lo=i
    else:
        if c[i]<c[lo]:lo=i
        if c[i]>=c[lo]*1.08:
            waves.append((last,lo,-1));last=lo;mode=1;hi=i
for tf in ['1h','4h','1d']:
    r=pd.read_csv(O/f'replay_{tf}.csv');r['T']=pd.to_datetime(r['T'],utc=True)
    for a,b,s in waves:
        if t.iloc[a]<r['T'].min() or t.iloc[b]>r['T'].max():continue
        if t.iloc[b]-t.iloc[a]!=pd.Timedelta(hours=b-a):continue
        q=r[(r['T']>=t.iloc[a])&(r['T']<=t.iloc[b])]
        if q.empty or q['T'].min()>t.iloc[a]+pd.Timedelta(tf) or q['T'].max()<t.iloc[b]-pd.Timedelta(tf) or (q['T'].diff().dropna()>pd.Timedelta(tf)).any():continue
        for model in ['original','lag_fixed','fallback_contract']:
            hit=q[q[model]==s];pre=r[r['T']<=t.iloc[a]]
            inherited=bool(len(pre) and pre[model].iloc[-1]==s)
            waveout.append({'tf':tf,'model':model,'start':str(t.iloc[a]),'end':str(t.iloc[b]),'s':s,'move_pct':s*(c[b]/c[a]-1)*100,'hit':len(hit)>0,'already_active_at_start':inherited,'lag_h':(hit['T'].iloc[0]-t.iloc[a]).total_seconds()/3600 if len(hit) else np.nan})
pd.DataFrame(res).to_csv(O/'pace_sensitivity.csv',index=False);W=pd.DataFrame(waveout);W.to_csv(O/'waves_8pct_cases.csv',index=False);z=W.groupby(['tf','model']).agg(n=('hit','size'),coverage=('hit','mean'),inherited=('already_active_at_start','mean'),lag_h=('lag_h','median'));z.to_csv(O/'waves_8pct_summary.csv');print(pd.DataFrame(res).to_string(index=False));print(z.to_string())
