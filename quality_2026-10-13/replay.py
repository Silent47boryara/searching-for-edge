import os,time,json,hashlib,ast,bisect
os.environ['MPLCONFIGDIR']='/private/tmp/bos_mpl'
from pathlib import Path
import numpy as np,pandas as pd
from scipy.signal import lfilter
from ta.trend import EMAIndicator,ADXIndicator,MACD
from ta.volatility import AverageTrueRange
from ta.momentum import RSIIndicator,StochasticOscillator
P=Path('/Users/arefevoleg/bot_project_v2');O=Path(__file__).parent

def indicators(c,h,l):
    a=2/51; ema,_=lfilter([a],[1,-(1-a)],c,zi=[(1-a)*c[0]])
    tr=np.maximum(h-l,np.maximum(np.abs(h-np.r_[c[0],c[:-1]]),np.abs(l-np.r_[c[0],c[:-1]])));tr[0]=h[0]-l[0]
    atr=np.zeros(len(c));atr[13]=tr[:14].mean();atr[14:],_=lfilter([1/14],[1,-13/14],tr[14:],zi=[13/14*atr[13]])
    return ema,atr

def kernel(c,h,l,v,ema,atr,inclusive=False,fallback=False):
    m=len(c);t=np.arange(m);vm=np.convolve(v,np.ones(20)/20,'full')[:m];vm[:19]=np.nan
    ph=np.zeros(m,dtype=bool);pl=ph.copy()
    ph[2:-2]=(h[2:-2]>=np.maximum.reduce([h[:-4],h[1:-3],h[2:-2],h[3:-1],h[4:]]))
    pl[2:-2]=(l[2:-2]<=np.minimum.reduce([l[:-4],l[1:-3],l[2:-2],l[3:-1],l[4:]]))
    hi=np.flatnonzero(ph&(h-ema>.7*atr)&(v>1.05*vm)&(t>=49));lo=np.flatnonzero(pl&(ema-l>.7*atr)&(v>1.05*vm)&(t>=49))
    up=np.zeros(m,dtype=bool);dn=up.copy();lev=np.full(m,np.nan)
    if len(hi) and len(lo):
        ih=np.searchsorted(hi,t-2,side='right' if inclusive else 'left')-1;il=np.searchsorted(lo,t-2,side='right' if inclusive else 'left')-1;valid=(ih>=0)&(il>=0)
        hv=h[hi[np.maximum(ih,0)]];lv=l[lo[np.maximum(il,0)]]
        up=valid&(c>hv*1.001);dn=valid&~up&(c<lv*.999);lev=np.where(up,hv,np.where(dn,lv,np.nan))
    ev=np.where(up&~np.r_[False,up[:-1]],1,np.where(dn&~np.r_[False,dn[:-1]],-1,0))
    pivotH=np.flatnonzero(ph);pivotL=np.flatnonzero(pl)
    hp=np.searchsorted(pivotH,t-2,side='right')-1;lp=np.searchsorted(pivotL,t-2,side='right')-1
    his=np.where(hp>=0,pivotH[np.maximum(hp,0)] if len(pivotH) else -1,-1);los=np.where(lp>=0,pivotL[np.maximum(lp,0)] if len(pivotL) else -1,-1)
    cur=0;start=-1;initial=np.nan;lastdir=0;laststart=-1;lastend=-1;endwhy='';conf=0
    for j in range(m):
        if cur:
            pi=los[j] if cur==1 else his[j]
            level=(l[pi] if cur==1 else h[pi]) if pi>start else initial if fallback else np.nan
            if (c[j]<level*.999 if cur==1 else c[j]>level*1.001):lastdir,laststart,lastend,endwhy=cur,start,j,'pivot' if pi>start else 'initial_level';cur=0
        s=ev[j]
        if s:
            if not cur:cur=s;start=j;initial=lev[j];conf=0
            elif s==cur:conf+=1
            else:lastdir,laststart,lastend,endwhy=cur,start,j,'opposite_bos';cur=s;start=j;initial=lev[j];conf=0
    if cur:
        pi=los[-1] if cur==1 else his[-1];br=(l[pi] if cur==1 else h[pi]) if pi>start else initial
        return 1,cur,start,np.nan,br,conf
    if lastdir:return 2,lastdir,laststart,lastend,np.nan,0
    return 0,0,-1,np.nan,np.nan,0

def load():
    old=pd.read_csv(P/'BTCUSDT_1h_history_full.csv');old['t']=pd.to_datetime(old['Open time'],utc=True)
    new=pd.read_csv(P/'LAB_attrib_p1/raw/BTCUSDT_1h_binance_raw.csv');new['t']=pd.to_datetime(new.open_time_ms,unit='ms',utc=True)
    cols=['Open','High','Low','Close','Volume']; ov=old.merge(new,on='t',suffixes=('_old','_new'));err={c:float((ov[c+'_old']-ov[c+'_new']).abs().max()) for c in cols}
    print('OVERLAP',len(ov),err,flush=True)
    bad=np.column_stack([(ov[c+'_old']-ov[c+'_new']).abs().to_numpy()>1e-5 for c in cols]).any(axis=1)
    if bad.any():
        assert bad.sum()==1 and ov.loc[bad,'t'].iloc[0]==old.t.max(),'unexplained overlap conflict'
        ov.loc[bad].to_csv(O/'overlap_last_partial.csv',index=False)
        print('RESOLVED last old unfinished candle by later closed exchange record',str(old.t.max()),flush=True)
    d=pd.concat([old[['t']+cols],new[['t']+cols]]).drop_duplicates('t',keep='last').sort_values('t').reset_index(drop=True)
    gaps=d['t'].diff().dropna()!=pd.Timedelta(hours=1)
    gap_rows=d.loc[gaps[gaps].index,['t']].copy();gap_rows['previous']=d.t.shift().loc[gap_rows.index];gap_rows.to_csv(O/'hourly_gaps.csv',index=False)
    print('GAPS',gap_rows.to_dict('records'),flush=True)
    assert ((d.High>=d[['Open','Close','Low']].max(axis=1))&(d.Low<=d[['Open','Close','High']].min(axis=1))).all()
    frames={'1h':d};qa={'overlap_rows':len(ov),'overlap_max_abs':err,'hourly_rows':len(d),'start':str(d.t.min()),'end':str(d.t.max()),'gaps':int(gaps.sum())}
    for tf,n in [('4h',4),('1d',24)]:
        g=d.set_index('t').resample(tf);a=g.agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'});cnt=g.Close.count();a=a[cnt==n].reset_index();frames[tf]=a
        r=pd.read_csv(P/f'LAB_attrib_p1/raw/BTCUSDT_{tf}_binance_raw.csv');r['t']=pd.to_datetime(r.open_time_ms,unit='ms',utc=True);z=a.merge(r,on='t',suffixes=('_a','_r'));delta={c:float((z[c+'_a']-z[c+'_r']).abs().max()) for c in cols};qa[tf]={'rows':len(a),'overlap':len(z),'max_abs':delta}
        assert max(delta.values())<1e-5,qa[tf]
    json.dump(qa,open(O/'data_qa.json','w'),indent=2);return frames

def exact_functions():
    src=(P/'bot_v2.py').read_text();tree=ast.parse(src);names=['add_indicators','_detect_swings','find_all_bos','_local_pivots','compute_impulse']
    ns=dict(pd=pd,np=np,bisect=bisect,SWING_LAG=2,EMAIndicator=EMAIndicator,ADXIndicator=ADXIndicator,MACD=MACD,AverageTrueRange=AverageTrueRange,RSIIndicator=RSIIndicator,StochasticOscillator=StochasticOscillator)
    txt='\n\n'.join(ast.get_source_segment(src,n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names)
    exec(txt,ns);(O/'original_core.py').write_text('import bisect\nimport numpy as np\nimport pandas as pd\nSWING_LAG=2\nfrom ta.trend import EMAIndicator,ADXIndicator,MACD\nfrom ta.volatility import AverageTrueRange\nfrom ta.momentum import RSIIndicator,StochasticOscillator\n'+txt)
    # explicit isolated candidate; display fallback omitted until actual pivot; state fix inclusive
    fixed=txt.replace('bisect.bisect_left(hi_idx, cutoff)','bisect.bisect_right(hi_idx, cutoff)').replace('bisect.bisect_left(lo_idx, cutoff)','bisect.bisect_right(lo_idx, cutoff)')
    fixed=fixed.replace('(float(x[\'level\']) if x[\'level\'] else None)','None')
    (O/'candidate_core.py').write_text('import bisect\nimport numpy as np\nimport pandas as pd\nSWING_LAG=2\nfrom ta.trend import EMAIndicator,ADXIndicator,MACD\nfrom ta.volatility import AverageTrueRange\nfrom ta.momentum import RSIIndicator,StochasticOscillator\n'+fixed)
    return ns

def run():
    frames=load();ns=exact_functions();rng=np.random.default_rng(20261013);val=[]
    for tf,d in frames.items():
        arr=d[['Close','High','Low','Volume']].to_numpy().T
        for k in np.unique(np.r_[np.linspace(499,len(d)-1,25,dtype=int),len(d)-1]):
            w=d.iloc[k-498:k+1].copy().reset_index(drop=True);w['Open time']=w.t.dt.tz_localize(None);b=ns['add_indicators'](w.copy());c,h,l,v=arr[:,k-498:k+1];e,a=indicators(c,h,l)
            assert np.allclose(e[49:],b.EMA_50.iloc[49:],rtol=1e-11);assert np.allclose(a,b.ATR,rtol=1e-11)
            z=ns['compute_impulse'](b,closed_only=False,tf=tf);r=kernel(c,h,l,v,e,a)
            state={0:'NONE',1:'ACTIVE',2:'ENDED'}[r[0]];dr={0:None,1:'BULL',-1:'BEAR'}[r[1]]
            assert z['state']==state and z.get('direction')==dr,(tf,k,z,r)
            if r[2]>=0:
                ts=w.t.iloc[r[2]];s=str(ts.date()) if tf=='1d' else ts.strftime('%d.%m %H:%M');assert s==z['start_time'],(tf,k,s,z)
            if r[0]==1:assert np.isclose(r[4],z['break_level']), (tf,k,z,r)
            val.append({'tf':tf,'k':int(k),'ok':True})
        # candidate AST agrees too
        candidate={};exec((O/'candidate_core.py').read_text(),candidate)
        for k in np.linspace(499,len(d)-1,10,dtype=int):
            w=d.iloc[k-498:k+1].copy().reset_index(drop=True);w['Open time']=w.t.dt.tz_localize(None);b=candidate['add_indicators'](w.copy());c,h,l,v=arr[:,k-498:k+1];e,a=indicators(c,h,l);r=kernel(c,h,l,v,e,a,True,False);z=candidate['compute_impulse'](b,closed_only=False,tf=tf)
            assert z['state']=={0:'NONE',1:'ACTIVE',2:'ENDED'}[r[0]] and z.get('direction')=={0:None,1:'BULL',-1:'BEAR'}[r[1]],(tf,k,z,r)
        print('VALIDATED',tf,len(val),flush=True)
    pd.DataFrame(val).to_csv(O/'validation.csv',index=False)
    for tf,d in frames.items():
        arr=d[['Close','High','Low','Volume']].to_numpy().T;rows=[];mins={'1h':60,'4h':240,'1d':1440}[tf];tic=time.time()
        for k in range(499,len(d)):
            if d.t.iloc[k]-d.t.iloc[k-498]!=pd.Timedelta(minutes=mins*498):continue
            c,h,l,v=arr[:,k-498:k+1];e,a=indicators(c,h,l);row={'T':d.t.iloc[k]+pd.Timedelta(minutes=mins),'close':c[-1],'atr':a[-1],'ema20':float(pd.Series(c).ewm(span=20,adjust=False).mean().iloc[-1]),'ret3':c[-1]-c[-4]}
            for H in [6,12,24]:row[f'past{H}']=(c[-1]-c[-1-H])/a[-1];row[f'fwd{H}']=(arr[0,k+H]/c[-1]-1)*100 if k+H<len(d) and d.t.iloc[k+H]-d.t.iloc[k]==pd.Timedelta(minutes=mins*H) else np.nan
            for name,inc,fall in [('original',False,False),('lag_fixed',True,False),('fallback_contract',True,True)]:
                z=kernel(c,h,l,v,e,a,inc,fall);row[name]=z[1] if z[0]==1 else 0;row[name+'_state']=z[0];row[name+'_dir']=z[1];row[name+'_start']=str(d.t.iloc[k-498+z[2]]) if z[2]>=0 else '';row[name+'_break']=z[4]
            rows.append(row)
            if len(rows)%5000==0:print('PROGRESS',tf,len(rows),round(time.time()-tic,1),flush=True)
        R=pd.DataFrame(rows);R.to_csv(O/f'replay_{tf}.csv',index=False);print('DONE',tf,len(R),round(time.time()-tic,1),flush=True)
if __name__=='__main__':run()
