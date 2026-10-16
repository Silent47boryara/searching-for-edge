import os,json
os.environ['MPLCONFIGDIR']='/private/tmp/bos_mpl'
from pathlib import Path
import numpy as np,pandas as pd
O=Path(__file__).parent;P=Path('/Users/arefevoleg/bot_project_v2');rng=np.random.default_rng(20261013)
G=pd.read_csv(P/'gamma_snapshot_agg.csv',usecols=['snapshot_ts_utc']);gt=pd.to_datetime(G.snapshot_ts_utc,format='ISO8601',utc=True);g0,g1=gt.min(),gt.max()
models=['original','lag_fixed','fallback_contract','ema20','momentum3','neutral']
def conf(y,p):return np.bincount((y.astype(int)+1)*3+p.astype(int)+1,minlength=9).reshape(3,3)
def scores(cm):
    diag=np.diag(cm);rec=diag/np.maximum(cm.sum(axis=1),1);prec=diag/np.maximum(cm.sum(axis=0),1);f=2*prec*rec/np.maximum(prec+rec,1e-20)
    present=cm.sum(axis=1)>0
    return float(rec[present].mean()),float(f[present].mean())
rows=[];diffs=[];null=[];sens=[];forw=[];evrows=[];cis=[];confrows=[]
for tf in ['1h','4h','1d']:
    r=pd.read_csv(O/f'replay_{tf}.csv',parse_dates=['T']);r['T']=pd.to_datetime(r['T'],utc=True);r['ema20']=np.where(r.close-r.ema20>.5*r.atr,1,np.where(r.close-r.ema20<-.5*r.atr,-1,0));r['momentum3']=np.where(r.ret3>r.atr,1,np.where(r.ret3<-r.atr,-1,0));r['neutral']=0
    r['reference']=np.where(r.past12>1,1,np.where(r.past12<-1,-1,0))
    for scope,q in [('all',r),('gamma',r[(r['T']>=g0)&(r['T']<=g1)])]+[(str(y),v) for y,v in r.groupby(r['T'].dt.year)]:
        y=q.reference.to_numpy();n=len(q)
        if not n:continue
        for model in models:
            p=q[model].to_numpy().astype(int);cm=conf(y,p);ba,f1=scores(cm);a=p!=0;active=int(a.sum());switch=int(np.sum(p[1:]!=p[:-1]));bull=p==1;bear=p==-1
            rows.append({'tf':tf,'scope':scope,'model':model,'n':n,'BA':ba,'macroF1':f1,'active_pct':100*a.mean(),'active_flat_pct':100*np.mean(y[a]==0) if active else np.nan,'active_opposite_pct':100*np.mean(y[a]==-p[a]) if active else np.nan,'active_same_pct':100*np.mean(y[a]==p[a]) if active else np.nan,'bull_precision':100*np.mean(y[bull]==1) if bull.any() else np.nan,'bear_precision':100*np.mean(y[bear]==-1) if bear.any() else np.nan,'switches':switch,'switches_per_day':switch/max((q['T'].max()-q['T'].min()).total_seconds()/86400,1),'reference_flat_pct':100*np.mean(y==0)})
            if scope in ['all','gamma']:
                for iy in range(3):
                    for ip in range(3):confrows.append({'tf':tf,'scope':scope,'model':model,'true':iy-1,'pred':ip-1,'n':int(cm[iy,ip])})
                fwd=q.fwd12.to_numpy();valid=a&np.isfinite(fwd)
                forw.append({'tf':tf,'scope':scope,'model':model,'n_active_with_future':int(valid.sum()),'signed_median_pct':float(np.median(p[valid]*fwd[valid])) if valid.any() else np.nan,'signed_mean_pct':float(np.mean(p[valid]*fwd[valid])) if valid.any() else np.nan,'positive_pct':float(100*np.mean(p[valid]*fwd[valid]>0)) if valid.any() else np.nan})
        if scope not in ['all','gamma']:continue
        for model in ['lag_fixed','fallback_contract']:diffs.append({'tf':tf,'scope':scope,'model':model,'n':n,'state_direction_changed_pct':100*np.mean(q.original!=q[model]),'start_changed_pct':100*np.mean(q.original_start.fillna('')!=q[model+'_start'].fillna(''))})
        for H in [6,12,24]:
            for K in [.5,1,2]:
                sy=np.where(q[f'past{H}']>K,1,np.where(q[f'past{H}']<-K,-1,0))
                for model in models:sens.append({'tf':tf,'scope':scope,'H':H,'K':K,'model':model,'BA':scores(conf(sy,q[model].to_numpy()))[0]})
        # "broken clock" comparison: shift the whole persisted signal, not independent coin flips.
        for model in ['original','lag_fixed']:
            p=q[model].to_numpy().astype(int);actual=scores(conf(y,p))[0];minshift={'1h':168,'4h':42,'1d':7}[tf]
            if n>2*minshift:
                shifts=rng.integers(minshift,n-minshift,1000);v=np.array([scores(conf(y,np.roll(p,int(s))))[0] for s in shifts]);null.append({'tf':tf,'scope':scope,'model':model,'BA':actual,'null_median':np.median(v),'null_q025':np.quantile(v,.025),'null_q975':np.quantile(v,.975),'p_shift':(1+np.sum(v>=actual))/1001})
        # paired 7-day block bootstrap of confusion matrices, 1000 repetitions
        blocks=(q['T'].astype('int64')//(7*86400*10**9)).to_numpy();unique=np.unique(blocks)
        if len(unique)>=5:
            cms={m:np.array([conf(y[blocks==b],q[m].to_numpy()[blocks==b]) for b in unique]) for m in ['original','lag_fixed','ema20','momentum3']}
            draw=rng.integers(0,len(unique),(1000,len(unique)))
            for a,b in [('lag_fixed','original'),('original','ema20'),('lag_fixed','ema20'),('lag_fixed','momentum3')]:
                ds=np.array([scores(cms[a][ix].sum(axis=0))[0]-scores(cms[b][ix].sum(axis=0))[0] for ix in draw]);cis.append({'tf':tf,'scope':scope,'a':a,'b':b,'blocks':len(unique),'delta_BA':scores(conf(y,q[a].to_numpy()))[0]-scores(conf(y,q[b].to_numpy()))[0],'lo':np.quantile(ds,.025),'hi':np.quantile(ds,.975)})
    # start timestamps; gamma common sample for phase2a
    step=pd.Timedelta(tf);q=r[(r['T']>=pd.Timestamp('2026-08-29 11:28:12',tz='UTC'))&(r['T']<=pd.Timestamp('2026-10-07 09:00',tz='UTC'))].copy()
    for model in ['original','lag_fixed','fallback_contract']:
        starts=pd.to_datetime(q[model+'_start'],utc=True,errors='coerce');mask=(q[model]!=0)&(starts==q['T']-step)
        for i in q.index[mask]:
            k=r.index.get_loc(i);H=int(pd.Timedelta(hours=24)/step);s=int(r.loc[i,model]);valid=k+H<len(r) and r['T'].iloc[k+H]-r['T'].iloc[k]==pd.Timedelta(hours=24)
            evrows.append({'tf':tf,'model':model,'T':str(r['T'].iloc[k]),'s':s,'R24':s*(r.close.iloc[k+H]/r.close.iloc[k]-1)*100 if valid else np.nan})
    print('METRICS',tf,flush=True)
for name,data in [('metrics',rows),('variant_changes',diffs),('shift_null',null),('sensitivity',sens),('forward_active',forw),('events',evrows),('block_ci',cis),('confusion',confrows)]:pd.DataFrame(data).to_csv(O/(name+'.csv'),index=False)
M=pd.DataFrame(rows);print(M[(M.scope.isin(['all','gamma']))].to_string(index=False));print('CHANGES',pd.DataFrame(diffs).to_string(index=False));print('NULL',pd.DataFrame(null).to_string(index=False));print('CI',pd.DataFrame(cis).to_string(index=False));print('EVENT',pd.DataFrame(evrows).groupby(['tf','model']).R24.agg(['count','median']).to_string())
