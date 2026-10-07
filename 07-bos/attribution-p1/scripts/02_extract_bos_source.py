"""Дословное извлечение BOS/impulse-кода из bot_v2.py (БЕЗ импорта модуля: он вызывает logging.basicConfig
в боевой bot_errors.log). Секреты не копируются: берутся только перечисленные определения."""
import ast, hashlib
SRC="/Users/arefevoleg/bot_project_v2/bot_v2.py"; OUT="/Users/arefevoleg/bot_project_v2/LAB_attrib_p1/scripts/bot_v2_extracted.py"
txt=open(SRC,encoding="utf-8").read(); h=hashlib.sha256(txt.encode()).hexdigest()
tree=ast.parse(txt)
FUNCS={"add_indicators","_detect_swings","find_all_bos","_local_pivots","compute_impulse"}; CONSTS={"SWING_LAG"}
parts=[]
for n in tree.body:
    if isinstance(n,ast.FunctionDef) and n.name in FUNCS: parts.append(ast.get_source_segment(txt,n))
    if isinstance(n,ast.Assign) and any(getattr(t,'id',None) in CONSTS for t in n.targets): parts.append(ast.get_source_segment(txt,n))
assert len([p for p in parts if p.startswith("def ")])==len(FUNCS), "не все функции найдены"
hdr=f'''# АВТОГЕНЕРАЦИЯ. Дословная копия из bot_v2.py, sha256 исходника = {h}
# Не редактировать вручную. Секретов здесь нет.
import bisect
import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, EMAIndicator, ADXIndicator
from ta.volatility import AverageTrueRange
SOURCE_SHA256 = "{h}"

'''
open(OUT,"w",encoding="utf-8").write(hdr+"\n\n".join(parts)+"\n")
print("sha256 bot_v2.py:",h); print("извлечено блоков:",len(parts))
