from pathlib import Path
import pandas as pd,json
P=Path(__file__).parent;d=pd.read_csv(P.parent/'collectors_2026-10-14/hourly_features.csv');cols=['T','price','oi','oi4','funding','r4','rv4','liq_usd','liq_imb','tape_usd','tape_flow','tape_flow_screen','gamma_A','gamma_size','liq_cov','tape_cov','gamma_available_ns','gamma_snapshot_ns'];d=d[cols];d['T']=pd.to_datetime(d['T'],utc=True).astype('int64')//10**6
rows=json.loads(d.to_json(orient='records'));js=(P/'chart.umd.min.js').read_text();html=(P/'template.html').read_text().replace('__LIB__',js).replace('__DATA__',json.dumps(rows,separators=(',',':'),ensure_ascii=False));(P/'market_map.html').write_text(html)
print('Created',len(rows),'hourly observations',len(html),'characters')
