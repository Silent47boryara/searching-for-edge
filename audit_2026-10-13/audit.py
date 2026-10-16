import os
os.environ['MPLCONFIGDIR']='/private/tmp/bos_mpl'
import ast, bisect, hashlib, json
from pathlib import Path
import pandas as pd, numpy as np
from ta.momentum import RSIIndicator,StochasticOscillator
from ta.trend import MACD,EMAIndicator,ADXIndicator
from ta.volatility import AverageTrueRange
P=Path('/Users/arefevoleg/bot_project_v2'); O=Path(__file__).parent
src=(P/'bot_v2.py').read_text(); tree=ast.parse(src)
names={'add_indicators','_detect_swings','find_all_bos','_local_pivots','compute_impulse','_imp_dir','describe_layers','compute_market_structure'}
code='\n\n'.join(ast.get_source_segment(src,n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names)
ns=dict(pd=pd,np=np,bisect=bisect,SWING_LAG=2,RSIIndicator=RSIIndicator,StochasticOscillator=StochasticOscillator,MACD=MACD,EMAIndicator=EMAIndicator,ADXIndicator=ADXIndicator,AverageTrueRange=AverageTrueRange)
exec(code,ns)
G=pd.read_csv(P/'gamma_snapshot_agg.csv'); G['T']=pd.to_datetime(G.snapshot_ts_utc,format='ISO8601',utc=True)
L=pd.concat([pd.read_csv(f).assign(source=f.name) for f in P.glob('btc_signals_log(*)_v4.csv')],ignore_index=True)
L['T']=pd.to_datetime(L.Time,utc=True); L=L.drop_duplicates('T').sort_values('T'); L=L[(L.T if False else L['T'])>=G['T'].min()]
print('GAMMA',len(G),G['T'].min(),G['T'].max(),'LOG',len(L),L['T'].min(),L['T'].max())
price=L[['T','Price']].copy().reset_index(drop=True)
print('LOG PRICE extrema',price.loc[price.Price.idxmin()].to_dict(),price.loc[price.Price.idxmax()].to_dict())
for hours in [6,24,72,168]:
    a=price.copy(); a['target']=a['T']-pd.Timedelta(hours=hours)
    z=pd.merge_asof(a,price.rename(columns={'T':'prev_T','Price':'prev_P'}),left_on='target',right_on='prev_T',tolerance=pd.Timedelta(minutes=65),direction='backward'); z['ret']=(z.Price/z.prev_P-1)*100
    print('RET',hours,z.loc[z.ret.idxmax(),['T','prev_T','Price','prev_P','ret']].to_dict(),z.loc[z.ret.idxmin(),['T','prev_T','Price','prev_P','ret']].to_dict())
# largest peak in actual logged prices; broad surrounding interval
peak=price.loc[price.Price.idxmax(),'T']; start=peak-pd.Timedelta(days=6); end=peak+pd.Timedelta(days=5)
cols=['T','Price','IMP_State','IMP_Direction','IMP_Start_Time','IMP_Break_Level','H4_IMP_State','H4_IMP_Direction','H4_IMP_Start_Time','H1_IMP_State','H1_IMP_Direction','H1_IMP_Start_Time','Layers_Head','Layers_Note','Main_Direction','SMC_Label']
Q=L[(L['T']>=start)&(L['T']<=end)][cols].copy()
statecols=['IMP_State','IMP_Direction','H4_IMP_State','H4_IMP_Direction','H1_IMP_State','H1_IMP_Direction']
change=Q[statecols].fillna('').ne(Q[statecols].fillna('').shift()).any(axis=1)
Q.to_csv(O/'peak_log.csv',index=False); Q[change].to_csv(O/'peak_transitions.csv',index=False)
print('PEAK transitions\n',Q[change].to_string(index=False))
for pref in ['IMP_','H4_IMP_','H1_IMP_']:
    print(pref,L[pref+'State'].value_counts().to_dict())
wrong=L.apply(lambda r: 'структура согласована' in str(r.Layers_Note) and any(r[p+'State']!='ACTIVE' for p in ['IMP_','H4_IMP_','H1_IMP_']),axis=1)
print('FALSE AGREEMENT',int(wrong.sum())); print(L.loc[wrong,cols].head(3).to_string(index=False))
print('SOURCE HASH',hashlib.sha256(src.encode()).hexdigest())
json.dump({'gamma_start':str(G['T'].min()),'gamma_end':str(G['T'].max()),'peak':str(peak),'false_agreement':int(wrong.sum()),'source_sha256':hashlib.sha256(src.encode()).hexdigest()},open(O/'summary.json','w'),indent=2)
# candles, isolated exact production functions, no imports of production module
raws={}
for tf in ['1h','4h','1d']:
    d=pd.read_csv(P/f'LAB_attrib_p1/raw/BTCUSDT_{tf}_binance_raw.csv'); d['Open time']=pd.to_datetime(d.open_time_ms,unit='ms'); raws[tf]=d
    print('CANDLES',tf,len(d),d['Open time'].min(),d['Open time'].max())
# snapshot at dates around price peak: rolling 500 bars including current, historical current fully formed but impulse discards it
for ts in [peak-pd.Timedelta(days=3),peak-pd.Timedelta(days=1),peak,peak+pd.Timedelta(days=1),peak+pd.Timedelta(days=3)]:
    for tf,d in raws.items():
        w=d[d['Open time']<=ts.tz_localize(None)].tail(500).copy().reset_index(drop=True)
        if ts.tz_localize(None)>d['Open time'].max()+pd.Timedelta(tf.replace('d',' days').replace('h',' hours')): continue
        w=ns['add_indicators'](w); out=ns['compute_impulse'](w,tf=tf)
        print('SNAP',str(ts),tf,{k:out.get(k) for k in ['state','direction','start_time','start_price','price','break_level','end_time','move_pct']})
# causality: full-series events must equal prefix events at a specific bar, fixed indicator history
for tf,d in raws.items():
    w=ns['add_indicators'](d.copy()); full={t:(s,lv) for t,s,lv in ns['find_all_bos'](w)}; bad=[]
    for t in np.linspace(100,len(w)-1,60,dtype=int):
        short={i:(s,lv) for i,s,lv in ns['find_all_bos'](w.iloc[:t+1])}
        if full.get(t)!=short.get(t): bad.append(int(t))
    print('EVENT PREFIX',tf,'60 checked',bad)
# synthetic boundary and fallback probes
w=pd.DataFrame({'Open time':pd.date_range('2026-01-01',periods=60,freq='h'),'High':np.full(60,100.),'Low':np.full(60,90.),'Close':np.full(60,95.),'Volume':np.full(60,100.),'EMA_50':np.full(60,95.),'ATR':np.ones(60)})
w.loc[10,['Low','Volume']]=[80,300]; w.loc[20,['High','Volume']]=[110,300]; w.loc[22,['High','Close']]=[112,111];w.loc[23,['High','Close']]=[113,112]
print('LAG PROBE',ns['find_all_bos'](w))
print('LAYER PROBE',ns['describe_layers'](*[{'state':'ENDED','direction':'BULL'}]*3))
# chart observed log price/states; ENDED explicitly blank
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,axs=plt.subplots(4,1,figsize=(13,8),sharex=True,gridspec_kw={'height_ratios':[3,1,1,1]})
axs[0].plot(Q['T'],Q.Price,color='black');axs[0].axvline(peak,color='red',ls='--');axs[0].set_ylabel('BTC spot, USD');axs[0].set_title('Observed BTC price and logged ACTIVE BOS states (UTC)')
for ax,pref,label in zip(axs[1:],['IMP_','H4_IMP_','H1_IMP_'],['1D','4H','1H']):
    vals=np.where(Q[pref+'State']=='ACTIVE',np.where(Q[pref+'Direction']=='BULL',1,-1),0)
    ax.step(Q['T'],vals,where='post');ax.set_yticks([-1,0,1]);ax.set_yticklabels(['BEAR','inactive','BULL']);ax.set_ylabel(label);ax.grid(alpha=.2)
fig.autofmt_xdate();fig.tight_layout();fig.savefig(O/'peak_bos.png',dpi=150)
