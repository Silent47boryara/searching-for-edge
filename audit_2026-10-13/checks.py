import ast,bisect,hashlib,json
from pathlib import Path
import pandas as pd,numpy as np
from ta.momentum import RSIIndicator,StochasticOscillator
from ta.trend import MACD,EMAIndicator,ADXIndicator
from ta.volatility import AverageTrueRange
P=Path('/Users/arefevoleg/bot_project_v2');O=Path(__file__).parent
src=(P/'bot_v2.py').read_text();tree=ast.parse(src)
names=['add_indicators','_detect_swings','find_all_bos','_local_pivots','compute_impulse','_imp_dir','describe_layers','compute_market_structure']
ns=dict(pd=pd,np=np,bisect=bisect,SWING_LAG=2,RSIIndicator=RSIIndicator,StochasticOscillator=StochasticOscillator,MACD=MACD,EMAIndicator=EMAIndicator,ADXIndicator=ADXIndicator,AverageTrueRange=AverageTrueRange)
exec('\n\n'.join(ast.get_source_segment(src,n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names),ns)
old=ast.parse((P/'LAB_attrib_p1/scripts/bot_v2_extracted.py').read_text())
for name in names:
    a=next((n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name),None);b=next((n for n in old.body if isinstance(n,ast.FunctionDef) and n.name==name),None)
    if a and b:print('AST SAME',name,ast.dump(a)==ast.dump(b))
G=pd.read_csv(P/'gamma_snapshot_agg.csv');gt=pd.to_datetime(G.snapshot_ts_utc,format='ISO8601',utc=True)
L=pd.concat([pd.read_csv(f) for f in P.glob('btc_signals_log(*)_v4.csv')],ignore_index=True);L['T']=pd.to_datetime(L.Time,utc=True);L=L.sort_values('T').drop_duplicates('T');L=L[(L['T']>=gt.min())&(L['T']<=gt.max())]
print('STRICT GAMMA WINDOW',len(L),L['T'].min(),L['T'].max())
for a,b in [('2026-09-15','2026-09-24'),('2026-10-01','2026-10-04')]:
    q=L[(L['T']>=pd.Timestamp(a,tz='UTC'))&(L['T']<pd.Timestamp(b,tz='UTC'))]
    cols=['T','Price','IMP_State','IMP_Direction','IMP_Break_Level','H4_IMP_State','H4_IMP_Direction','H1_IMP_State','H1_IMP_Direction','Main_Direction','SMC_Label','Layers_Note']
    print('WINDOW EXTREMA',a,q.loc[q.Price.idxmin(),cols].to_dict(),q.loc[q.Price.idxmax(),cols].to_dict())
    print('LARGEST LOG GAP',q['T'].diff().max())
print('AT FIRST BULL')
for pref in ['H1_IMP_','H4_IMP_','IMP_']:
    q=L[(L['T']>=pd.Timestamp('2026-09-16',tz='UTC'))&(L[pref+'State']=='ACTIVE')&(L[pref+'Direction']=='BULL')]
    print(pref,q.iloc[0][['T','Price',pref+'Start_Time',pref+'Start_Price']].to_dict())
# exact snapshots from nearest real logged ticks: matches historical event and level fields
rows=[]
for ts in ['2026-09-18 04:17:52','2026-09-18 16:19:43','2026-09-19 00:20:58','2026-09-23 04:59:20','2026-09-23 10:18:52','2026-09-23 22:54:50','2026-10-02 13:36:05','2026-10-02 19:38:40']:
    log=L.iloc[(L['T']-pd.Timestamp(ts,tz='UTC')).abs().argmin()]
    for tf,pref in [('1h','H1_IMP_'),('4h','H4_IMP_'),('1d','IMP_')]:
        d=pd.read_csv(P/f'LAB_attrib_p1/raw/BTCUSDT_{tf}_binance_raw.csv');d['Open time']=pd.to_datetime(d.open_time_ms,unit='ms');w=d[d['Open time']<=log['T'].tz_localize(None)].tail(500).copy().reset_index(drop=True)
        w=ns['add_indicators'](w);z=ns['compute_impulse'](w,tf=tf)
        r={'T':str(log['T']),'tf':tf,'log_state':log[pref+'State'],'replay_state':z.get('state'),'log_dir':log[pref+'Direction'],'replay_dir':z.get('direction'),'log_start':log[pref+'Start_Time'],'replay_start':z.get('start_time'),'log_break':log[pref+'Break_Level'],'replay_break':z.get('break_level')};rows.append(r)
print('POINT REPLAY\n',pd.DataFrame(rows).to_string(index=False));pd.DataFrame(rows).to_csv(O/'point_replay.csv',index=False)
# Real no-pivot fallback cases: displayed level crossed at bar CLOSE with ACTIVE state retained.
for tf in ['1h','4h','1d']:
    d=pd.read_csv(P/f'LAB_attrib_p1/raw/BTCUSDT_{tf}_binance_raw.csv');d['Open time']=pd.to_datetime(d.open_time_ms,unit='ms');cases=[]
    for k in range(max(499,len(d)-450),len(d)-1):
        if d.loc[k,'Open time']<pd.Timestamp('2026-08-24'):continue
        w=ns['add_indicators'](d.iloc[k-498:k+2].copy().reset_index(drop=True));z=ns['compute_impulse'](w,tf=tf)
        if z.get('state')=='ACTIVE' and z.get('break_pivot_time') is None:
            s=1 if z['direction']=='BULL' else -1;lv=z.get('break_level');c=z['price']
            if lv and (c<lv*.999 if s==1 else c>lv*1.001):cases.append({'T':str(d.loc[k,'Open time']),'direction':z['direction'],'close':c,'display_break':lv})
    print('REAL FALSE BREAK',tf,cases[:8],'N',len(cases))
# Controlled state-machine probe isolates fallback contract. Not market evidence.
w=pd.DataFrame({'Open time':pd.date_range('2026-01-01',periods=60,freq='h'),'High':np.linspace(110,100,60),'Low':np.linspace(100,80,60),'Close':np.linspace(105,90,60),'Volume':100.,'ATR':1.,'EMA_50':95.})
orig=ns['find_all_bos'];ns['find_all_bos']=lambda d:[(55,1,100.)];z=ns['compute_impulse'](w,closed_only=False,tf='1h');ns['find_all_bos']=orig
print('FALLBACK PROBE',{k:z.get(k) for k in ['state','direction','price','break_level','dist_to_break_pct','break_pivot_time']})
# Selection boundary: actual code excludes pivot i=t-2, despite docstring <=.
w.loc[:,'Close']=100.;w.loc[42,'Close']=85.;orig=ns['_detect_swings'];ns['_detect_swings']=lambda d:([(25,110.)],[(30,90.),(40,80.)]);print('BOUNDARY PROBE',ns['find_all_bos'](w));ns['_detect_swings']=orig
# Detect timestamp + lag on 4h end, known outage
q=L[(L['T']>=pd.Timestamp('2026-09-23',tz='UTC'))&(L['T']<pd.Timestamp('2026-09-24',tz='UTC'))];print('SEP23 TICKS',q[['T','Price','H4_IMP_State','H4_IMP_End_Time']].to_string(index=False))
print('HASH UNCHANGED',hashlib.sha256((P/'bot_v2.py').read_bytes()).hexdigest())
