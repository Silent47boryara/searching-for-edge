from pathlib import Path
import pandas as pd,numpy as np,re,json,time
P=Path('/Users/arefevoleg/bot_project_v2');O=Path(__file__).parent;END=pd.Timestamp('2026-10-14T00:00Z');START=pd.Timestamp('2026-08-29T11:28:12Z');qa={}
def ts(x):return pd.to_datetime(x,format='ISO8601',utc=True)
def ns(x):return pd.Timestamp(x).value
print('MARK read',flush=True);parts=[];n=0
for c in pd.read_csv(P/'funding_markprice_raw.csv',usecols=['recv_ts_utc','mark_price','funding_rate'],chunksize=300000):
    c['t']=ts(c.recv_ts_utc);c=c[(c.t>=START)&(c.t<=END)].sort_values('t');n+=len(c);c['minute']=c.t.dt.floor('min')+pd.Timedelta(minutes=1)
    parts.append(c.groupby('minute').agg(n=('mark_price','size'),close=('mark_price','last'),last=('t','last'),funding=('funding_rate','last')))
m=pd.concat(parts).groupby(level=0).agg({'n':'sum','close':'last','last':'last','funding':'last'}).sort_index();m=m[m.index<=END].reindex(pd.date_range(START.ceil('min'),END,freq='min'));m.index.name='T';m['good']=(m.n>=40)&((m.index.to_series()-m['last']).dt.total_seconds()<=60);m['p']=m.close.where(m.good);m['r']=np.log(m.p).diff();m['sq']=m.r**2
m.to_csv(O/'minute_mark.csv');qa['mark']={'rows':n,'minutes':len(m),'good_minutes':int(m.good.sum()),'start':str(m.index.min()),'end':str(m.index.max())}
H=pd.date_range(START.ceil('h'),END,freq='h');D=pd.DataFrame(index=H);D.index.name='T';D['price']=m.p.reindex(H);D['funding']=m.funding.reindex(H).where((H.to_series()-m['last'].reindex(H)).dt.total_seconds()<=60)
for h in [1,4,24]:
    nmin=h*60;pc=m.p.shift(nmin).reindex(H);D[f'r{h}']=np.log(D.price/pc)
    cnt=m.sq.rolling(nmin,min_periods=1).count();rv=np.sqrt(m.sq.rolling(nmin,min_periods=1).sum())
    D[f'rv{h}']=rv.reindex(H).where(cnt.reindex(H)>=.9*nmin)
    # sum of minute returns at (T,T+h], right edge known in future only for target
    fcnt=cnt.shift(-nmin);frv=rv.shift(-nmin)
    D[f'yret{h}']=np.log(m.p.shift(-nmin).reindex(H)/D.price).where(fcnt.reindex(H)>=.9*nmin)
    D[f'yrv{h}']=frv.reindex(H).where(fcnt.reindex(H)>=.9*nmin)
D['logrv4']=np.log(D.rv4);D['logrv24']=np.log(D.rv24);D['yvol4']=np.log(D.yrv4);D['yvol24']=np.log(D.yrv24)
# OI causal asof
print('OI',flush=True);oi=pd.read_csv(P/'oi_raw.csv');oi['t']=ts(oi.recv_ts_utc);oi=oi[oi.t<=END].sort_values('t');ot=oi.t.astype('int64').to_numpy();ov=oi.open_interest.to_numpy()
def asof(arrt,arrv,t,age):
    i=np.searchsorted(arrt,ns(t),side='right')-1
    return arrv[i] if i>=0 and ns(t)-arrt[i]<=age*10**9 else np.nan
D['oi']= [asof(ot,ov,t,900) for t in H];D['oi4']=[np.log(asof(ot,ov,t,900)/asof(ot,ov,t-pd.Timedelta(hours=4),900)) for t in H]
# logs & coverage masks
LINE=re.compile(r'^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d),\d+ (\w+) (.*)$')
def logrows(stem):
    rows=[]
    for f in P.glob(stem+'*'):
        if f.suffix not in ['.log','.1','.2','.3']:continue
        for ln in f.open(errors='replace'):
            match=LINE.match(ln)
            if match:
                t=pd.Timestamp(match[1],tz='UTC')-pd.Timedelta(hours=3)
                if t<=END:rows.append((t,match[2],match[3]))
    return sorted(rows,key=lambda x:x[0])
def union(iv):
    result=[]
    for a,b in sorted(iv):
        if b<=a:continue
        if result and a<=result[-1][1]:result[-1][1]=max(result[-1][1],b)
        else:result.append([a,b])
    return result
L=logrows('liq_collector.log');bad=[];down=None;hb=None
for t,l,msg in L:
    if l=='ERROR' and down is None:down=t
    if msg.startswith('Подключено') and down is not None:bad.append([down,t]);down=None
    if 'heartbeat' in msg:
        if hb is not None and t-hb>pd.Timedelta(minutes=15):bad.append([hb,t])
        hb=t
if down is not None:bad.append([down,END])
if hb is not None and END-hb>pd.Timedelta(minutes=15):bad.append([hb,END])
lbad=union(bad);pd.DataFrame(lbad,columns=['start','end']).to_csv(O/'liq_bad_windows.csv',index=False)
def coverage(iv,a,b):return max(0,1-sum(max(0,(min(b,y)-max(a,x)).total_seconds()) for x,y in iv)/(b-a).total_seconds())
lq=pd.read_csv(P/'liquidations_raw.csv',usecols=['recv_ts_utc','liquidation_side','notional_usd']);lq['t']=ts(lq.recv_ts_utc);lq=lq[(lq.t>=START)&(lq.t<=END)].sort_values('t');lt=lq.t.astype('int64').to_numpy();lv=lq.notional_usd.to_numpy();ls=np.where(lq.liquidation_side=='SHORT_LIQUIDATION',1,-1);lc=np.r_[0,np.cumsum(lv)];li=np.r_[0,np.cumsum(lv*ls)]
for T in H:
    a=T-pd.Timedelta(hours=4);cov=coverage(lbad,a,T) if a>=START else 0;D.loc[T,'liq_cov']=cov
    if cov>=.9:
        lo=np.searchsorted(lt,ns(a),side='right');hi=np.searchsorted(lt,ns(T),side='right');v=lc[hi]-lc[lo];D.loc[T,'liq_usd']=v;D.loc[T,'liq_activity']=np.log1p(v);D.loc[T,'liq_imb']=(li[hi]-li[lo])/v if v>0 else 0
qa['liq']={'events':len(lq),'bad_windows':len(lbad),'heartbeat_last':str(hb)}
# tape causal receive time and old frozen reliability masks
print('TAPE',flush=True);tp=pd.read_csv(P/'deribit_option_trades_raw.csv',usecols=['recv_ts_utc','timestamp_ms','trade_id','instrument_name','direction','amount','index_price','block_trade_id','combo_id','block_rfq_id']);tp['recv']=ts(tp.recv_ts_utc);tp=tp[(tp.recv<=END)].drop_duplicates('trade_id').sort_values('timestamp_ms');tt=tp.timestamp_ms.to_numpy()*10**6;rt=tp.recv.astype('int64').to_numpy();u=(tp.amount*tp.index_price).to_numpy();sign=np.where(tp.direction=='buy',1,-1)*np.where(tp.instrument_name.str[-1]=='C',1,-1);block=(tp.block_trade_id.notna()|tp.combo_id.notna()|tp.block_rfq_id.notna()).to_numpy();tl=logrows('deribit_trade_tape_collector.log');th=[t for t,_,msg in tl if 'heartbeat' in msg];tb=[]
for a,b in zip(th[:-1],th[1:]):
    if b-a>pd.Timedelta(minutes=15):tb.append([a,b])
old=json.load(open(P/'LAB_attrib_p1/out/outage_windows_by_stream.json'));firstlog=tl[0][0] if tl else END
# old masked source windows before retained rotation; conservative shared-machine outages included
for a,b in old['funding']:
    a=pd.Timestamp(a,tz='UTC');b=pd.Timestamp(b,tz='UTC')
    if a<firstlog and b-a>pd.Timedelta(minutes=15):tb.append([a,min(b,firstlog)])
tb.append([pd.Timestamp('2026-10-02T00:00Z'),pd.Timestamp('2026-10-06T23:05Z')])
if th and END-th[-1]>pd.Timedelta(minutes=15):tb.append([th[-1],END])
tb=union(tb);pd.DataFrame(tb,columns=['start','end']).to_csv(O/'tape_bad_windows.csv',index=False)
for T in H:
    a=T-pd.Timedelta(hours=4);cov=coverage(tb,a,T) if a>=tp.recv.min() else 0;D.loc[T,'tape_cov']=cov
    if cov<.9:continue
    lo=np.searchsorted(tt,ns(a),side='right');hi=np.searchsorted(tt,ns(T),side='right');ok=rt[lo:hi]<=ns(T);us=u[lo:hi];sg=sign[lo:hi];bb=block[lo:hi]
    for suffix,k in [('',ok),('_screen',ok&~bb)]:
        total=us[k].sum();D.loc[T,'tape_usd'+suffix]=total;D.loc[T,'tape_activity'+suffix]=np.log1p(total);D.loc[T,'tape_flow'+suffix]=np.sum(us[k]*sg[k])/total if total>0 else 0
qa['tape']={'trades':len(tp),'block_combo_notional_pct':float(100*u[block].sum()/u.sum()),'receive_lag_seconds_quantiles':{str(k):float(v) for k,v in pd.Series((rt-tt)/1e9).quantile([.5,.9,.99]).items()},'old_mask_before_retained_log':str(firstlog)}
# gamma snapshots freshly aggregated, availability = successful log completion, not start timestamp
print('GAMMA read',flush=True);parts=[]
for c in pd.read_csv(P/'gamma_snapshot_raw.csv',usecols=['snapshot_ts_utc','spot_price','strike','gamma_exposure_per_1pct_move'],chunksize=300000):
    c['t']=ts(c.snapshot_ts_utc);c=c[c.t<=END];sp=c.spot_price;k=c.strike;g=c.gamma_exposure_per_1pct_move
    c['up']=np.where((k>sp)&(k<=sp*1.05),g,0);c['dn']=np.where((k<sp)&(k>=sp*.95),g,0)
    parts.append(c.groupby('t').agg(up=('up','sum'),dn=('dn','sum'),spot=('spot_price','first')))
g=pd.concat(parts).groupby(level=0).agg({'up':'sum','dn':'sum','spot':'first'}).sort_index();g['gamma_A']=(g.up-g.dn)/(g.up+g.dn);g['gamma_size']=np.log1p(g.up+g.dn);g['available']=pd.NaT
sn=g.index.astype('int64').to_numpy();matched=0;delays=[]
for t,level,msg in logrows('gamma_collector.log'):
    mt=re.search(r'snapshot ok: spot=(\d+) n=(\d+)',msg)
    if not mt:continue
    j=np.searchsorted(sn,ns(t),side='right')-1
    if j<0:continue
    if 0<=ns(t)-sn[j]<=1200*10**9 and abs(g.spot.iloc[j]-float(mt[1]))<=1.1:
        key=g.index[j]
        if pd.isna(g.loc[key,'available']) or t<g.loc[key,'available']:g.loc[key,'available']=t;matched+=1;delays.append((ns(t)-sn[j])/1e9)
g['available']=pd.to_datetime(g.available,utc=True);g=g.dropna(subset=['available']).sort_values('available');g.to_csv(O/'gamma_observable.csv');av=g.available.astype('int64').to_numpy()
for T in H:
    j=np.searchsorted(av,ns(T),side='right')-1
    if j<0:continue
    x=g.iloc[j];st=g.index[j]
    if T-st>pd.Timedelta(minutes=20) or (st>=pd.Timestamp('2026-10-02T10:10Z') and st<pd.Timestamp('2026-10-06T23:10Z')):continue
    D.loc[T,'gamma_A']=x.gamma_A;D.loc[T,'gamma_size']=x.gamma_size;D.loc[T,'gamma_available_ns']=ns(x.available);D.loc[T,'gamma_snapshot_ns']=ns(st)
qa['gamma']={'aggregated_snapshots':sum(len(x) for x in parts),'unique_matched_completed':len(g),'completion_delays_q_sec':{str(k):float(v) for k,v in pd.Series(delays).quantile([.5,.9,.99,1]).items()}}
D['oi_funding']=D.oi4*D.funding;D['oi_liq_activity']=D.oi4*D.liq_activity;D['oi_liq_imb']=D.oi4*D.liq_imb;D['oi_tape']=D.oi4*D.tape_flow;D['funding_liq']=D.funding*D.liq_imb;D['gamma_tape']=D.gamma_A*D.tape_flow;D['liq_tape']=D.liq_imb*D.tape_flow
D.to_csv(O/'hourly_features.csv');qa['available_hourly']={c:int(D[c].notna().sum()) for c in ['r1','r4','logrv4','logrv24','yret4','yvol4','oi4','funding','liq_imb','gamma_A','tape_flow']};json.dump(qa,open(O/'data_qa.json','w'),indent=2);print(json.dumps(qa,indent=2),flush=True)
