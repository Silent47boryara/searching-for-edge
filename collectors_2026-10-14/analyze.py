from pathlib import Path
import numpy as np,pandas as pd,json
from scipy.stats import spearmanr,rankdata
O=Path(__file__).parent;D=pd.read_csv(O/'hourly_features.csv',index_col=0,parse_dates=True);D.index=pd.to_datetime(D.index,utc=True);D=D[D.index.hour%4==0]
BASE=['r1','r4','logrv4','logrv24'];SINGLES={'OI':['oi4'],'funding':['funding'],'liquidations':['liq_activity','liq_imb'],'gamma':['gamma_A','gamma_size'],'tape':['tape_activity','tape_flow']}
PAIRS={'OI+funding':('OI','funding',['oi_funding']),'OI+liquidations':('OI','liquidations',['oi_liq_activity','oi_liq_imb']),'OI+tape':('OI','tape',['oi_tape']),'funding+liquidations':('funding','liquidations',['funding_liq']),'gamma+tape':('gamma','tape',['gamma_tape']),'liquidations+tape':('liquidations','tape',['liq_tape'])}
GROUPS=dict(SINGLES)
for name,(a,b,x) in PAIRS.items():GROUPS[name]=SINGLES[a]+SINGLES[b]+x
GROUPS['all5']=list(dict.fromkeys(sum(SINGLES.values(),[])+sum([p[2] for p in PAIRS.values()],[])))
RNG=np.random.default_rng(20261014);ORIGIN=D.index.min();FIRST=ORIGIN+pd.Timedelta(days=14)
def predict(train,test,cols,target):
    x=train[cols].to_numpy();v=test[cols].to_numpy();mu=x.mean(0);sd=x.std(0);sd=np.where(sd>1e-14,sd,1);x=(x-mu)/sd;v=(v-mu)/sd;y=train[target].to_numpy();ym=y.mean();coef=np.linalg.solve(x.T@x+10*np.eye(x.shape[1]),x.T@(y-ym));return v@coef+ym

def walk(q,cols,target,others=None):
    outs=[];cut=FIRST;fold=0
    while cut<=D.index.max():
        train=q[q.index+pd.Timedelta(hours=4)<=cut];test=q[(q.index>=cut)&(q.index<cut+pd.Timedelta(days=7))]
        if len(train)>=max(36,2*len(cols)+10) and len(test)>=8:
            pred=predict(train,test,cols,target);pb=predict(train,test,BASE,target);r=pd.DataFrame({'T':test.index,'y':test[target].to_numpy(),'pred':pred,'baseline':pb,'fold':fold,'train_n':len(train)})
            if others:
                for name,c in others.items():r[name]=predict(train,test,c,target)
            assert train.index.max()+pd.Timedelta(hours=4)<=test.index.min()
            outs.append(r)
        cut+=pd.Timedelta(days=7);fold+=1
    return pd.concat(outs,ignore_index=True) if outs else pd.DataFrame()

def paired(r,against='baseline'):
    y=r.y.to_numpy();eb=(r[against].to_numpy()-y)**2;ea=(r.pred.to_numpy()-y)**2;delta=eb-ea
    b=r['T'].dt.floor('D').astype('int64').to_numpy();u=np.unique(b);n=np.array([np.sum(b==x) for x in u]);ds=np.array([delta[b==x].sum() for x in u]);bs=np.array([eb[b==x].sum() for x in u]);actual=ds.sum();sign=RNG.choice([-1,1],size=(10000,len(u)));p=(1+np.sum(sign@ds>=actual))/(10001)
    draw=RNG.integers(0,len(u),(1000,len(u)));db=ds[draw].sum(1);bb=bs[draw].sum(1);imp=100*db/np.maximum(bb,1e-30)
    fold=r.assign(eb=eb,ea=ea).groupby('fold').agg(eb=('eb','mean'),ea=('ea','mean'));wins=int((fold.ea<fold.eb).sum())
    out={'n':len(r),'days':len(u),'folds':len(fold),'fold_wins':wins,'MSE_improvement_pct':100*delta.mean()/max(eb.mean(),1e-30),'CI_lo':np.quantile(imp,.025),'CI_hi':np.quantile(imp,.975),'p':p,'baseline_MSE':eb.mean(),'augmented_MSE':ea.mean()}
    if np.abs(y).mean()<.1:out.update({'direction_hit_pct':100*np.mean(np.sign(r.pred)==np.sign(y)),'baseline_hit_pct':100*np.mean(np.sign(r[against])==np.sign(y))})
    return out

results=[];preds=[];synergy=[]
for group,features in GROUPS.items():
    for target in ['yret4','yvol4']:
        cols=BASE+features;q=D.dropna(subset=cols+[target]);others={}
        if group in PAIRS:
            a,b,_=PAIRS[group];others={'single_left':BASE+SINGLES[a],'single_right':BASE+SINGLES[b]}
        r=walk(q,cols,target,others)
        if len(r):
            z=paired(r);z.update({'group':group,'target':target,'eligible_n':len(q),'test_start':str(r['T'].min()),'test_end':str(r['T'].max())});results.append(z);r['group']=group;r['target']=target;preds.append(r)
            for other in others:
                w=paired(r,other);w.update({'group':group,'target':target,'against':other});synergy.append(w)
        else:results.append({'group':group,'target':target,'eligible_n':len(q),'n':0,'p':1})
        print('MODEL',group,target,'eligible',len(q),'tested',len(r),flush=True)
R=pd.DataFrame(results);pv=R.p.fillna(1).to_numpy();order=np.argsort(pv);adjust=np.maximum.accumulate(pv[order]*(len(pv)-np.arange(len(pv))));R['p_Holm']=0.;R.loc[order,'p_Holm']=np.minimum(adjust,1);R.to_csv(O/'model_results.csv',index=False);pd.concat(preds,ignore_index=True).to_csv(O/'predictions.csv',index=False);pd.DataFrame(synergy).to_csv(O/'pair_vs_components.csv',index=False)
print(R[['group','target','eligible_n','n','days','folds','fold_wins','MSE_improvement_pct','CI_lo','CI_hi','p','p_Holm']].to_string(index=False),flush=True)
# descriptive contemporaneous and future, no p screening or selection
corr=[]
for feature in sum(SINGLES.values(),[]):
    for outcome in ['r4','logrv4','yret4','yvol4','yret24','yvol24']:
        q=D.dropna(subset=list(dict.fromkeys(BASE+[feature,outcome])))
        if len(q)<12:continue
        rho=spearmanr(q[feature],q[outcome]).statistic
        x=np.column_stack([np.ones(len(q))]+[rankdata(q[c]) for c in BASE if c!=outcome]);a=rankdata(q[feature]);b=rankdata(q[outcome]);ra=a-x@np.linalg.lstsq(x,a,rcond=None)[0];rb=b-x@np.linalg.lstsq(x,b,rcond=None)[0];partial=np.corrcoef(ra,rb)[0,1] if ra.std()>1e-12 and rb.std()>1e-12 else np.nan
        corr.append({'feature':feature,'outcome':outcome,'n':len(q),'rho':rho,'partial_rank':partial})
pd.DataFrame(corr).to_csv(O/'descriptive_correlations.csv',index=False)
# all predetermined event types, thresholds from initial14 days only
train=D[D.index<FIRST];defs={}
for col in ['liq_activity','tape_activity','gamma_size']:defs[col+'_high']=float(train[col].quantile(.9))
defs['funding_hi']=float(train.funding.quantile(.9));defs['funding_lo']=float(train.funding.quantile(.1));json.dump(defs,open(O/'event_thresholds.json','w'),indent=2)
TEST=D[D.index>=FIRST].copy();events={'high_liquidations':TEST.liq_activity>defs['liq_activity_high'],'OI_down+high_liquidations':(TEST.oi4<0)&(TEST.liq_activity>defs['liq_activity_high']),'OI_up+positive_price+high_funding':(TEST.oi4>0)&(TEST.r4>0)&(TEST.funding>defs['funding_hi']),'OI_up+negative_price+low_funding':(TEST.oi4>0)&(TEST.r4<0)&(TEST.funding<defs['funding_lo']),'high_tape_activity':TEST.tape_activity>defs['tape_activity_high'],'high_gamma_size':TEST.gamma_size>defs['gamma_size_high']}
ER=[];cases=[]
for name,mask in events.items():
    validcols= ['liq_activity'] if name=='high_liquidations' else ['liq_activity','oi4'] if name.startswith('OI_down') else ['oi4','funding','r4'] if name.startswith('OI_up') else ['tape_activity'] if name=='high_tape_activity' else ['gamma_size']
    q=TEST.dropna(subset=BASE+['yret4','yvol4']+validcols);ev=q[mask.reindex(q.index)];ctl=q[~mask.reindex(q.index)]
    if not len(ev) or len(ctl)<5:continue
    # nearest three controls in pre-event price and volatility, no future used in matching
    sd=train[BASE].std().replace(0,1);mu=train[BASE].mean();cx=((ctl[BASE]-mu)/sd).to_numpy();ex=((ev[BASE]-mu)/sd).to_numpy();matched=[]
    for i,(_,e) in enumerate(ev.iterrows()):
        dist=np.sum((cx-ex[i])**2,axis=1);j=np.argsort(dist)[:3];matched.extend(ctl.iloc[j].index.tolist());cases.append({'event':name,'T':str(e.name),'past4h_pct':100*np.expm1(e.r4),'future4h_pct':100*np.expm1(e.yret4),'future_rv4_pct':100*np.exp(e.yvol4),'oi4_pct':100*np.expm1(e.oi4),'funding':e.funding,'liq_usd':e.liq_usd,'tape_usd':e.tape_usd,'gamma_A':e.gamma_A,'nearest_distance':float(np.sqrt(dist[j[0]]))})
    mc=ctl.loc[matched]
    ER.append({'event':name,'N':len(ev),'unique_days':ev.index.floor('D').nunique(),'control_unique_n':mc.index.nunique(),'event_R4_mean_pct':100*np.expm1(ev.yret4).mean(),'event_R4_median_pct':100*np.expm1(ev.yret4).median(),'control_R4_mean_pct':100*np.expm1(mc.yret4).mean(),'control_R4_median_pct':100*np.expm1(mc.yret4).median(),'event_RV4_median_pct':100*np.exp(ev.yvol4).median(),'matched_RV4_median_pct':100*np.exp(mc.yvol4).median(),'event_absR4_median_pct':100*np.expm1(ev.yret4).abs().median(),'matched_absR4_median_pct':100*np.expm1(mc.yret4).abs().median()})
pd.DataFrame(ER).to_csv(O/'event_summary.csv',index=False);pd.DataFrame(cases).to_csv(O/'event_cases.csv',index=False)
# sensitivity restricted to existing model families containing tape: no second optimization
sens=[]
DS=D.copy();DS['tape_activity']=DS.tape_activity_screen;DS['tape_flow']=DS.tape_flow_screen
for name in ['oi_tape','gamma_tape','liq_tape']:
    left={'oi_tape':'oi4','gamma_tape':'gamma_A','liq_tape':'liq_imb'}[name];DS[name]=DS[left]*DS.tape_flow
for group in ['tape','OI+tape','gamma+tape','liquidations+tape','all5']:
    for target in ['yret4','yvol4']:
        cols=BASE+GROUPS[group];q=DS.dropna(subset=cols+[target]);r=walk(q,cols,target)
        if len(r):z=paired(r);z.update({'group':group,'target':target});sens.append(z)
pd.DataFrame(sens).to_csv(O/'screen_tape_sensitivity.csv',index=False)
print('EVENTS\n',pd.DataFrame(ER).to_string(index=False),flush=True);print('SCREEN\n',pd.DataFrame(sens).to_string(index=False),flush=True)
