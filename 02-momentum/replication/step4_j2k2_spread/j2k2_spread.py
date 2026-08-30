#!/usr/bin/env python3
"""
Lab 06 — реализация J=2 / K=2: 2-недельный momentum, 2-недельное удержание.

ПОСЛЕДНЯЯ допустимая реализация класса Momentum. Дальше параметры не
варьируются независимо от того, что получится.

Отношение к J=1/K=1 (step3): та же вселенная, тот же фильтр ликвидности,
та же модель издержек, те же три теста. Меняются ровно два параметра —
окно momentum и период удержания.

═════════════════════════════════════════════════════════════════════════════
ПРЕ-РЕГИСТРАЦИЯ — зафиксировано ДО расчёта, после просмотра не менять
═════════════════════════════════════════════════════════════════════════════

КАЛЕНДАРЬ
  ranking date = close воскресенья (последняя завершённая свеча до понедельника)
  momentum     = 14 календарных дней до ranking date
  entry        = open понедельника
  exit         = open понедельника через 14 дней
  Открытие-в-открытие на обоих концах, как в J=1/K=1.

НЕПЕРЕСЕКАЮЩИЕСЯ ПЕРИОДЫ — решение, требующее обоснования.
  При K=2 классическая схема Jegadeesh-Titman держит K перекрывающихся
  когорт с весом 1/K и ребалансирует еженедельно. Это даёт больше точек,
  но соседние наблюдения делят одну и ту же позицию — ряд автокоррелирован.
  Все три наших теста (bootstrap по периодам, sign-flip по периодам,
  permutation внутри периода) опираются на НЕЗАВИСИМОСТЬ наблюдений и на
  перекрывающемся ряде дали бы заниженные p-значения.
  Поэтому: непересекающиеся периоды, вход каждый второй понедельник.

  ФАЗА. Непересекающаяся схема делит понедельники на две фазы (чётные и
  нечётные). Выбор одной из них после просмотра результата был бы
  подгонкой, поэтому обе объявлены здесь заранее:
    PHASE_A (headline) — начиная с первого доступного понедельника, шаг 2
    PHASE_B (диагностика) — со сдвигом на неделю, шаг 2
  Вместе они покрывают все понедельники и ничего не отбрасывают.

ФИЛЬТР ЛИКВИДНОСТИ — тот же, что в J=1/K=1, без изменений:
  абсолютный порог 1 000 000 USDT по trailing 30d median дневного оборота.

КОРЗИНЫ: квинтили, верхний Long / нижний Short, равные веса.

ОБРАБОТКА ПРОПУСКОВ — та же, что в J=1/K=1:
  нет open на entry → символ не входит в корзину;
  нет open на exit  → forced close по последней доступной цене в окне;
  после entry цен нет вовсе → позиция неисполнима, учитывается отдельно.

ИЗДЕРЖКИ — импортируются из net_of_costs.py, не переопределяются:
  taker 0.05% × 2 стороны + слиппедж 0.05% × 2 стороны = 0.20% на ногу,
  0.40 пп на обе ноги ЗА ПЕРИОД УДЕРЖАНИЯ.

  ВАЖНО ПРИ СРАВНЕНИИ С J=1/K=1: при K=2 ребалансировка вдвое реже, поэтому
  0.40 пп приходятся на 2 недели, а не на 1. В пересчёте на неделю это
  0.20 пп против 0.40 пп у J=1/K=1 — вдвое дешевле по времени. Отчёт
  приводит обе нормировки.

FUNDING: реальные ставки за фактический период удержания; где данных нет —
  funding_missing, ноль не подставляется.
═════════════════════════════════════════════════════════════════════════════
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
STEP3 = HERE.parent / "step3_full_history_spread"
sys.path.insert(0, str(STEP3))

# Импортируем, а не переписываем: гарантия, что вселенная, фильтр, тесты и
# модель издержек буквально те же, что в J=1/K=1.
from full_history_spread import (          # noqa: E402
    LIQUIDITY_LOOKBACK_DAYS, MIN_LIQUIDITY_USDT, MIN_LIQUIDITY_OBS,
    N_QUANTILES, N_PERMUTATION, SEED,
    load_panels, at, bootstrap_ci, sign_flip,
)
from net_of_costs import (                 # noqa: E402
    TAKER_FEE_PCT, SLIPPAGE_PCT, SIDES_PER_LEG, COST_PER_LEG_PCT,
    load_funding,
)

# ── параметры J=2/K=2 ────────────────────────────────────────────────────────
MOMENTUM_LOOKBACK_DAYS = 14
HOLDING_DAYS           = 14
STEP_WEEKS             = 2          # непересекающиеся периоды
PHASES                 = {"A": 0, "B": 1}   # обе объявлены заранее
HEADLINE_PHASE         = "A"


def build_periods(op, cl, vol, phase_offset: int):
    """Тот же алгоритм, что в J=1/K=1, но с окнами 14d и шагом 2 недели."""
    idx = cl.index
    panel_end = idx.max()
    mondays = [d for d in idx if d.dayofweek == 0]
    entries = mondays[phase_offset::STEP_WEEKS]

    members, periods, unexec = [], [], []

    for entry_ts in entries:
        exit_ts = entry_ts + pd.Timedelta(days=HOLDING_DAYS)
        rank_ts = entry_ts - pd.Timedelta(days=1)
        mom_ts = rank_ts - pd.Timedelta(days=MOMENTUM_LOOKBACK_DAYS)

        c_rank, c_prev = at(cl, rank_ts), at(cl, mom_ts)
        ok_mom = c_rank.notna() & c_prev.notna() & (c_prev > 0) & (c_rank > 0)

        liq_win = vol.loc[(vol.index > rank_ts - pd.Timedelta(
            days=LIQUIDITY_LOOKBACK_DAYS)) & (vol.index <= rank_ts)]
        liq_obs = liq_win.notna().sum()
        liq_med = liq_win.median(skipna=True)
        ok_liq = (liq_obs >= MIN_LIQUIDITY_OBS) & liq_med.notna() & \
                 (liq_med >= MIN_LIQUIDITY_USDT)

        o_entry = at(op, entry_ts)
        ok_entry = o_entry.notna() & (o_entry > 0)

        eligible = ok_mom & ok_liq & ok_entry
        n_elig = int(eligible.sum())
        if n_elig < N_QUANTILES * 2:
            continue

        syms = eligible[eligible].index
        mom = (c_rank[syms] / c_prev[syms] - 1) * 100
        k = max(1, n_elig // N_QUANTILES)
        order = mom.sort_values(ascending=False)
        longs, shorts = list(order.index[:k]), list(order.index[-k:])

        o_exit = at(op, exit_ts)
        win = cl.loc[(cl.index > entry_ts) & (cl.index < exit_ts)]
        beyond_panel = exit_ts > panel_end

        legs = {"LONG": [], "SHORT": []}
        for side, bucket in (("LONG", longs), ("SHORT", shorts)):
            for s in bucket:
                e = float(o_entry[s])
                forced, reason = 0, ""
                xp = o_exit[s] if s in o_exit.index else np.nan
                if pd.isna(xp) or xp <= 0:
                    col = win[s].dropna() if s in win.columns else pd.Series(dtype=float)
                    col = col[col > 0]
                    if col.empty:
                        unexec.append({
                            "entry_date": entry_ts.date().isoformat(),
                            "symbol": s, "side": side, "entry_price": e,
                            "momentum_14d": round(float(mom[s]), 4),
                            "reason": "no_price_after_entry"})
                        continue
                    xp, forced = float(col.iloc[-1]), 1
                    reason = "panel_end" if beyond_panel else "missing_exit"
                else:
                    xp = float(xp)
                ret = (xp / e - 1) * 100
                legs[side].append(ret)
                members.append({
                    "entry_date": entry_ts.date().isoformat(),
                    "exit_date": exit_ts.date().isoformat(),
                    "symbol": s, "side": side,
                    "momentum_14d": round(float(mom[s]), 4),
                    "liquidity_30d_median": round(float(liq_med[s]), 2),
                    "entry_price": e, "exit_price": xp,
                    "return": round(ret, 4),
                    "forced_close_flag": forced, "forced_reason": reason})

        L, S = np.array(legs["LONG"]), np.array(legs["SHORT"])
        if len(L) == 0 or len(S) == 0:
            continue
        periods.append({
            "entry_date": entry_ts.date().isoformat(),
            "exit_date": exit_ts.date().isoformat(),
            "n_universe": n_elig, "n_long": len(L), "n_short": len(S),
            "long_mean": round(float(L.mean()), 4),
            "short_mean": round(float(S.mean()), 4),
            "long_median": round(float(np.median(L)), 4),
            "short_median": round(float(np.median(S)), 4),
            "spread_gross": round(float(L.mean() - S.mean()), 4),
            "spread_gross_median": round(float(np.median(L) - np.median(S)), 4)})

    return pd.DataFrame(members), pd.DataFrame(periods), pd.DataFrame(unexec)


def add_funding(m: pd.DataFrame) -> pd.DataFrame:
    """funding за фактический период удержания; нет данных → funding_missing=1."""
    m = m.copy()
    m["entry"] = pd.to_datetime(m["entry_date"])
    m["exit"] = pd.to_datetime(m["exit_date"])
    cache, fs, fm = {}, {}, {}
    for sym, g in m.groupby("symbol"):
        if sym not in cache:
            cache[sym] = load_funding(sym)
        s = cache[sym]
        for i, r in g.iterrows():
            if s.empty:
                fs[i], fm[i] = np.nan, 1
                continue
            wdw = s.loc[(s.index >= r["entry"]) & (s.index < r["exit"])]
            covered = (not wdw.empty and s.index.min() <= r["entry"]
                       and s.index.max() >= r["exit"] - pd.Timedelta(hours=8))
            if covered:
                fs[i], fm[i] = float(wdw.sum()) * 100, 0
            else:
                fs[i], fm[i] = np.nan, 1
    m["funding_pct"] = pd.Series(fs)
    m["funding_missing"] = pd.Series(fm)
    return m


def apply_costs(m: pd.DataFrame, p: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for d, g in m.groupby("entry_date"):
        L, S = g[g.side == "LONG"], g[g.side == "SHORT"]
        if L.empty or S.empty:
            continue
        gross = L["return"].mean() - S["return"].mean()
        net = gross - 2 * COST_PER_LEG_PCT
        fl_ok = int(L.funding_missing.sum()) == 0
        fs_ok = int(S.funding_missing.sum()) == 0
        if fl_ok and fs_ok:
            fL, fS = L.funding_pct.mean(), S.funding_pct.mean()
            net_f = net - fL + fS
        else:
            fL = fS = net_f = np.nan
        rows.append({
            "entry_date": d,
            "spread_gross": round(gross, 4),
            "costs_long": COST_PER_LEG_PCT, "costs_short": COST_PER_LEG_PCT,
            "spread_net": round(net, 4),
            "funding_long_pct": round(fL, 5) if fl_ok else np.nan,
            "funding_short_pct": round(fS, 5) if fs_ok else np.nan,
            "spread_net_with_funding": round(net_f, 4) if fl_ok and fs_ok else np.nan,
            "funding_coverage_pct": round((1 - g.funding_missing.mean()) * 100, 1)})
    out = pd.DataFrame(rows)
    return p.merge(out, on="entry_date", how="left", suffixes=("", "_x")) \
            .drop(columns=[c for c in out.columns if c + "_x" in p.columns],
                  errors="ignore")


def perm_test(m: pd.DataFrame, obs: float, rng) -> float:
    """Внутри периода монеты случайно перераспределяются между ногами,
    размеры корзин сохраняются, издержки применяются те же."""
    blocks = []
    for _, g in m.groupby("entry_date"):
        r = g["return"].to_numpy()
        nl = int((g.side == "LONG").sum()); ns = int((g.side == "SHORT").sum())
        if nl and ns:
            blocks.append((r, nl, ns))
    if not blocks:
        return float("nan")

    def stat():
        v = []
        for r, nl, ns in blocks:
            p = rng.permutation(r)
            v.append(p[:nl].mean() - p[nl:nl + ns].mean() - 2 * COST_PER_LEG_PCT)
        return float(np.mean(v))

    cnt = sum(abs(stat()) >= abs(obs) for _ in range(N_PERMUTATION))
    return (cnt + 1) / (N_PERMUTATION + 1)


def summarise(x: np.ndarray, label: str, rng, p_perm=np.nan) -> dict:
    lo, hi = bootstrap_ci(x, rng)
    ps = sign_flip(x, rng)
    return {"series": label, "n_periods": len(x),
            "mean_pct": round(float(x.mean()), 4),
            "median_pct": round(float(np.median(x)), 4),
            "periods_pos_pct": round(float((x > 0).mean() * 100), 1),
            "std_pp": round(float(x.std()), 3),
            "boot_ci_lo": round(lo, 4), "boot_ci_hi": round(hi, 4),
            "boot_excl_0": int(lo > 0 or hi < 0),
            "p_sign_flip": round(ps, 4),
            "p_permutation": round(p_perm, 4) if not np.isnan(p_perm) else np.nan}


def main():
    rng = np.random.default_rng(SEED)
    op, cl, vol = load_panels()
    print(f"\n[J2K2] momentum {MOMENTUM_LOOKBACK_DAYS}d, holding {HOLDING_DAYS}d, "
          f"непересекающиеся периоды, шаг {STEP_WEEKS} нед.")
    print(f"[J2K2] фильтр ликвидности ${MIN_LIQUIDITY_USDT:,} — тот же, что J1K1")

    res, store = [], {}
    for ph, off in PHASES.items():
        m, p, u = build_periods(op, cl, vol, off)
        if p.empty:
            continue
        m = add_funding(m)
        p = apply_costs(m, p)
        store[ph] = (m, p, u)
        print(f"[J2K2] фаза {ph}: периодов={len(p)}, позиций={len(m)}, "
              f"funding покрыт {100*(1-m.funding_missing.mean()):.1f}%")

    mA, pA, uA = store[HEADLINE_PHASE]
    gA = pA.spread_gross.to_numpy()
    nA = pA.spread_net.to_numpy()
    res.append(summarise(gA, f"GROSS фаза {HEADLINE_PHASE} (headline)", rng))
    res.append(summarise(nA, f"NET фаза {HEADLINE_PHASE} (headline)", rng,
                         perm_test(mA, float(nA.mean()), rng)))
    other = [k for k in store if k != HEADLINE_PHASE]
    if other:
        ph = other[0]
        mB, pB, _ = store[ph]
        res.append(summarise(pB.spread_gross.to_numpy(),
                             f"GROSS фаза {ph} (диагностика)", rng))
        res.append(summarise(pB.spread_net.to_numpy(),
                             f"NET фаза {ph} (диагностика)", rng,
                             perm_test(mB, float(pB.spread_net.mean()), rng)))
    rdf = pd.DataFrame(res)

    mA.drop(columns=["entry", "exit"], errors="ignore").to_csv(
        HERE / "basket_membership_j2k2.csv", sep=";", index=False)
    pA.to_csv(HERE / "period_spreads_j2k2.csv", sep=";", index=False)
    rdf.to_csv(HERE / "j2k2_summary.csv", sep=";", index=False)
    if not uA.empty:
        uA.to_csv(HERE / "unexecutable_j2k2.csv", sep=";", index=False)

    print("\n" + "=" * 104)
    print(f"{'ряд':<34}{'пер':>5}{'mean':>9}{'median':>9}{'>0':>7}"
          f"{'CI95':>22}{'p_sign':>8}{'p_perm':>8}")
    print("-" * 104)
    for _, r in rdf.iterrows():
        pp = "   н/д" if pd.isna(r.p_permutation) else f"{r.p_permutation:8.4f}"
        print(f"{r['series']:<34}{r.n_periods:>5}{r.mean_pct:>+9.3f}"
              f"{r.median_pct:>+9.3f}{r.periods_pos_pct:>6.1f}%"
              f"  [{r.boot_ci_lo:+7.3f}..{r.boot_ci_hi:+7.3f}]"
              f"{r.p_sign_flip:>8.4f}{pp}")

    g0, n0 = float(gA.mean()), float(nA.mean())
    print(f"\n  издержки: {2*COST_PER_LEG_PCT:.2f} пп за период (2 нед) = "
          f"{COST_PER_LEG_PCT:.2f} пп/нед — вдвое дешевле по времени, чем J1K1")
    print(f"  съедено: {g0-n0:.3f} пп из {g0:+.3f}% = "
          f"{(g0-n0)/abs(g0)*100:.1f}% валового спреда")

    write_md(rdf, pA, mA, store, uA)
    print(f"\n→ RESULT.md, period_spreads_j2k2.csv, basket_membership_j2k2.csv, "
          f"j2k2_summary.csv")


def write_md(rdf, pA, mA, store, uA):
    gr = rdf.iloc[0]; nt = rdf.iloc[1]
    g0, n0 = gr.mean_pct, nt.mean_pct
    n_sig = int(nt.boot_excl_0) + int(nt.p_sign_flip < 0.05) + \
            int(nt.p_permutation < 0.05 if pd.notna(nt.p_permutation) else 0)
    cov = 1 - mA.funding_missing.mean()
    n_fund = int(pA.spread_net_with_funding.notna().sum())

    L = []; A = L.append
    A("# Lab 06 — J=2 / K=2 (2-недельный momentum, 2-недельное удержание)\n\n")
    A(f"**Дата:** {pd.Timestamp.now().date().isoformat()}\n\n")
    A("**Последняя допустимая реализация класса Momentum.** Дальше параметры "
      "не варьируются независимо от результата.\n")

    A("\n## Пре-регистрация\n\n")
    A("| параметр | значение |\n|---|---|\n")
    A(f"| ranking date | close воскресенья |\n")
    A(f"| momentum | **{MOMENTUM_LOOKBACK_DAYS} календарных дней** до ranking date |\n")
    A(f"| entry | open понедельника |\n")
    A(f"| exit | open понедельника через **{HOLDING_DAYS} дней** |\n")
    A(f"| периоды | **непересекающиеся**, шаг {STEP_WEEKS} недели |\n")
    A(f"| корзины | квинтили, верхний Long / нижний Short, равные веса |\n")
    A(f"| фильтр ликвидности | {MIN_LIQUIDITY_USDT:,} USDT trailing "
      f"{LIQUIDITY_LOOKBACK_DAYS}d median — **тот же, что в J=1/K=1** |\n")

    A("\n### Почему непересекающиеся периоды\n")
    A("Классическая схема Jegadeesh-Titman при K=2 держит две перекрывающиеся "
      "когорты с весом 1/2 и ребалансирует еженедельно. Это даёт вдвое больше "
      "точек, но соседние наблюдения делят одну и ту же позицию — ряд "
      "автокоррелирован.\n\n")
    A("Все три наших теста (bootstrap по периодам, sign-flip по периодам, "
      "permutation внутри периода) опираются на **независимость наблюдений** "
      "и на перекрывающемся ряде дали бы заниженные p-значения. "
      "Поэтому взята непересекающаяся схема — меньше точек, но тесты остаются "
      "валидными.\n")

    A("\n### Про фазу\n")
    A("Непересекающаяся схема делит понедельники на две фазы. Выбор одной из "
      "них после просмотра результата был бы подгонкой, поэтому **обе объявлены "
      "заранее**: фаза A — headline, фаза B — диагностика. Вместе они "
      "покрывают все понедельники, ничего не отбрасывается.\n")

    A("\n## Издержки\n\n")
    A(f"Модель импортирована из `step3_full_history_spread/net_of_costs.py` "
      f"и не переопределялась: taker {TAKER_FEE_PCT}% × {SIDES_PER_LEG} стороны "
      f"+ слиппедж {SLIPPAGE_PCT}% × {SIDES_PER_LEG} стороны = "
      f"{COST_PER_LEG_PCT:.2f}% на ногу, **{2*COST_PER_LEG_PCT:.2f} пп на обе "
      f"ноги за период удержания**.\n\n")
    A(f"Слиппедж {SLIPPAGE_PCT}% — **допущение**, не измерение (как и в J=1/K=1).\n\n")
    A(f"**Существенно при сравнении с J=1/K=1:** при K=2 ребалансировка вдвое "
      f"реже, поэтому {2*COST_PER_LEG_PCT:.2f} пп приходятся на 2 недели. "
      f"В пересчёте на неделю это **{COST_PER_LEG_PCT:.2f} пп против "
      f"{2*COST_PER_LEG_PCT:.2f} пп** у J=1/K=1 — вдвое дешевле по времени. "
      f"Это главное экономическое отличие схемы.\n")

    A("\n## Результат\n\n")
    A("| ряд | периодов | mean | median | периодов >0 | bootstrap CI95 | CI≠0 | "
      "p sign-flip | p permutation |\n|---|---|---|---|---|---|---|---|---|\n")
    for _, r in rdf.iterrows():
        pp = "н/д" if pd.isna(r.p_permutation) else f"{r.p_permutation:.4f}"
        A(f"| {r['series']} | {r.n_periods} | **{r.mean_pct:+.3f}%** | "
          f"{r.median_pct:+.3f}% | {r.periods_pos_pct:.1f}% | "
          f"[{r.boot_ci_lo:+.3f} .. {r.boot_ci_hi:+.3f}] | "
          f"{'да' if r.boot_excl_0 else 'нет'} | {r.p_sign_flip:.4f} | {pp} |\n")

    A(f"\n### Сколько съедают издержки\n\n")
    A(f"- валовый спред: **{g0:+.3f}%** за 2 недели ({g0/2:+.3f}%/нед)\n")
    A(f"- издержки: **{2*COST_PER_LEG_PCT:.2f} пп** за период "
      f"({COST_PER_LEG_PCT:.2f} пп/нед)\n")
    A(f"- чистый спред: **{n0:+.3f}%** за 2 недели ({n0/2:+.3f}%/нед)\n")
    A(f"- **съедено: {g0-n0:.3f} пп = {(g0-n0)/abs(g0)*100:.1f}% валового**\n")

    A(f"\n### Сравнение с J=1/K=1 (step3)\n\n")
    A("| | J=1/K=1 | J=2/K=2 |\n|---|---|---|\n")
    A(f"| наблюдений | 338 недель | {gr.n_periods} периодов |\n")
    A(f"| gross за неделю | +0.573% | {g0/2:+.3f}% |\n")
    A(f"| издержки за неделю | 0.40 пп | {COST_PER_LEG_PCT:.2f} пп |\n")
    A(f"| **net за неделю** | **+0.173%** | **{n0/2:+.3f}%** |\n")
    A(f"| тестов пройдено (net) | 0 из 3 | {n_sig} из 3 |\n")
    A("\nНормировка на неделю нужна, иначе цифры несопоставимы: у J=2/K=2 "
      "период вдвое длиннее.\n")

    A("\n## Funding\n\n")
    A(f"Покрытие: **{cov*100:.1f}%** позиций, периодов с полным покрытием "
      f"корзины: **{n_fund}** из {len(pA)}.\n\n")
    if n_fund == 0:
        A("Ни одного периода с полным покрытием — вклад funding **не измерен, "
          "а не равен нулю**. Причина та же, что в J=1/K=1: архивы funding "
          "покрывают 2025-10…2026-05 по 372 символам, а вселенная шире и "
          "история длиннее. Считать по половине корзины означало бы скрытую "
          "подстановку.\n")
        cp = mA[mA.funding_missing == 0]
        if len(cp):
            fl = cp[cp.side == "LONG"].funding_pct
            fsh = cp[cp.side == "SHORT"].funding_pct
            if len(fl) and len(fsh):
                A(f"\nПо покрытым позициям ({len(cp)} шт.): средний funding за "
                  f"период удержания {fl.mean():+.4f}% у лонга и "
                  f"{fsh.mean():+.4f}% у шорта, что дало бы вклад около "
                  f"**{-fl.mean()+fsh.mean():+.4f} пп**. Ориентир по "
                  f"направлению, не оценка — выборка смещена и по символам, "
                  f"и по периоду.\n")
    else:
        sub = pA.dropna(subset=["spread_net_with_funding"])
        A(f"На покрытых периодах: net без funding {sub.spread_net.mean():+.3f}%, "
          f"с funding **{sub.spread_net_with_funding.mean():+.3f}%**, "
          f"вклад {sub.spread_net_with_funding.mean()-sub.spread_net.mean():+.3f} пп. "
          f"Выборка мала — оценка порядка величины.\n")
    A("\nНоль вместо отсутствующего funding не подставлялся; позиции помечены "
      "`funding_missing=1`.\n")

    if not uA.empty:
        A(f"\n## Неисполнимые позиции\n\n{len(uA)} позиций без единой цены "
          f"после входа — учтены отдельно, в спред не входят "
          f"(`unexecutable_j2k2.csv`).\n")

    A("\n## Вердикт по гейту PLAN.md\n\n")
    if n0 < 0 and nt.median_pct < 0:
        A(f"Спред после издержек **устойчиво отрицателен**: mean {n0:+.3f}%, "
          f"median {nt.median_pct:+.3f}%.\n\n**ЗАКРЫТЬ реализацию.** "
          f"Гипотеза momentum как таковая не закрывается — она подтверждена "
          f"не нами; закрывается эта конкретная параметризация на этой "
          f"вселенной.\n")
    elif n0 > 0 and n_sig >= 1:
        A(f"Спред после издержек **остаётся положительным** ({n0:+.3f}% за "
          f"период, {n0/2:+.3f}%/нед) и проходит **{n_sig} из 3** тестов "
          f"значимости.\n\n**ПЕРЕДАТЬ ДАЛЬШЕ на holdout.**\n")
    elif n0 > 0:
        A(f"Спред после издержек положителен ({n0:+.3f}% за период, "
          f"{n0/2:+.3f}%/нед), но **не проходит ни одного** теста значимости.\n\n"
          f"**Уходит в шум.** Это результат, а не ошибка: величина эффекта "
          f"того же порядка, что издержки и разброс.\n")
    else:
        A(f"Спред после издержек отрицателен по среднему ({n0:+.3f}%), но "
          f"медиана {nt.median_pct:+.3f}% знак не подтверждает — устойчивого "
          f"разворота нет.\n\n**Уходит в шум/отрицательное.** Фиксируется "
          f"честно как результат.\n")

    # ── устойчивость к выбору фазы: считаем фактически ───────────────────────
    if len(rdf) >= 4:
        nB = rdf.iloc[3]
        same_sign = (n0 > 0) == (nB.mean_pct > 0)
        A(f"\n### Устойчивость к выбору фазы — решающая проверка\n\n")
        A("| | фаза A (headline) | фаза B (диагностика) |\n|---|---|---|\n")
        A(f"| net mean | **{n0:+.3f}%** | **{nB.mean_pct:+.3f}%** |\n")
        A(f"| net median | {nt.median_pct:+.3f}% | {nB.median_pct:+.3f}% |\n")
        A(f"| периодов >0 | {nt.periods_pos_pct:.1f}% | {nB.periods_pos_pct:.1f}% |\n")
        A(f"| тестов пройдено | {n_sig} из 3 | "
          f"{int(nB.boot_excl_0)+int(nB.p_sign_flip<0.05)+int(pd.notna(nB.p_permutation) and nB.p_permutation<0.05)} из 3 |\n")
        A(f"\nРазница между фазами: **{abs(n0 - nB.mean_pct):.3f} пп**.\n\n")
        if not same_sign:
            A(f"**Фазы расходятся ПО ЗНАКУ.** Единственное различие между ними — "
              f"с какого понедельника начат отсчёт. Это произвольный выбор, не "
              f"несущий никакой рыночной информации, и он переворачивает знак "
              f"результата: {n0:+.3f}% против {nB.mean_pct:+.3f}%.\n\n")
            A("Такая чувствительность к сдвигу на одну неделю говорит, что "
              "наблюдаемая величина определяется не эффектом, а тем, какие "
              "конкретные двухнедельные окна попали в выборку. Это независимое "
              "от p-значений свидетельство в пользу вердикта «шум»: даже если "
              "бы фаза A прошла тесты, доверять ей было бы нельзя.\n")
        else:
            A(f"Фазы совпадают по знаку. Расхождение "
              f"{abs(n0 - nB.mean_pct):.3f} пп показывает разброс, вносимый "
              f"произвольным выбором стартовой недели.\n")
    A("\nФормулировки «доказано» / «опровергнуто» не используются: это "
      "гейт-решение о продолжении работы.\n")
    A(f"\n**Класс Momentum закрыт по параметрам.** J=1/K=1 и J=2/K=2 — обе "
      f"допустимые реализации отработаны; дальнейший подбор J и K был бы "
      f"подгонкой под результат.\n")

    A("\n## Файлы\n")
    A("- `j2k2_spread.py` — расчёт\n")
    A("- `period_spreads_j2k2.csv` — по периодам: ноги, gross, costs, net, funding\n")
    A("- `basket_membership_j2k2.csv` — позиции с funding и forced-флагами\n")
    A("- `j2k2_summary.csv` — сводка тестов по обеим фазам\n")

    (HERE / "RESULT.md").write_text("".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
