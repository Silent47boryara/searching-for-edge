#!/usr/bin/env python3
"""
Lab 06 Step 3 — пересчёт спреда NET OF COSTS.

Методология ranking / корзин / holding period НЕ меняется. Используются уже
посчитанные weekly_spreads.csv и basket_membership.csv; заново ничего не
сортируется. Добавляются только издержки.

╔══════════════════════════════════════════════════════════════════════════╗
║ МОДЕЛЬ ИЗДЕРЖЕК — зафиксирована до расчёта, под результат не подбиралась ║
╚══════════════════════════════════════════════════════════════════════════╝

1. КОМИССИЯ. Binance USDⓈ-M Futures, taker, VIP 0, без BNB-скидки: 0.0500%
   за сторону. Берётся taker, а не maker: momentum-ребалансировка требует
   входа по рынку в момент открытия недели, лимитное исполнение не
   гарантировано. Вход + выход = 2 стороны на ногу.

2. СЛИППЕДЖ. +5 бп на сторону входа и на сторону выхода.
   ЭТО ДОПУЩЕНИЕ, а не измерение. Реальный слиппедж зависит от размера
   позиции и стакана в конкретный момент; ни того, ни другого в данных нет.
   Число взято как round-number-ориентир, помечено допущением везде в отчёте.

   Итого на ногу за неделю: 2×(0.05% + 0.05%) = 0.20%.
   На обе ноги: 0.40 пп в неделю — вычитается из спреда.

3. FUNDING. Реальные ставки за фактический период удержания, суммой всех
   выплат в окне [entry, exit). Лонг платит funding, шорт получает.
   Источник: lab_03_bot1_oi_funding_price_divergence/data/funding/ (сырые
   архивы Binance).

   ГДЕ FUNDING НЕТ — позиция помечается funding_missing. НОЛЬ НЕ ПОДСТАВЛЯЕТСЯ:
   подстановка нуля означала бы утверждение «funding был нулевым», которого
   данные не подтверждают, и систематически занижала бы издержки.

ДВА СЛОЯ РЕЗУЛЬТАТА (следствие покрытия funding, а не выбор):
   Слой A — net of комиссии + слиппедж, ВСЯ история (100% позиций).
   Слой B — net of комиссии + слиппедж + funding, только недели с полным
            покрытием funding (значительно меньшая выборка).
"""

import io
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from full_history_spread import (          # noqa: E402
    N_BOOTSTRAP, N_SIGNFLIP, N_PERMUTATION, SEED,
    bootstrap_ci, sign_flip,
)

FUNDING_DIR = (HERE.parent.parent /
               "lab_03_bot1_oi_funding_price_divergence" / "data" / "funding")

# ── пред-объявленные издержки ────────────────────────────────────────────────
TAKER_FEE_PCT   = 0.0500   # Binance USDⓈ-M taker, VIP 0, без BNB-скидки
SLIPPAGE_PCT    = 0.0500   # ДОПУЩЕНИЕ: 5 бп на сторону
SIDES_PER_LEG   = 2        # вход + выход
COST_PER_LEG_PCT = SIDES_PER_LEG * (TAKER_FEE_PCT + SLIPPAGE_PCT)   # 0.20%
HOLDING_DAYS    = 7


def load_funding(sym: str) -> pd.Series:
    """Все выплаты funding по символу: индекс = время расчёта, значение = ставка."""
    d = FUNDING_DIR / sym
    if not d.exists():
        return pd.Series(dtype=float)
    parts = []
    for f in sorted(d.glob("*.zip")):
        try:
            with zipfile.ZipFile(f) as z:
                raw = z.read(z.namelist()[0])
        except Exception:
            continue
        if not raw:
            continue
        try:
            x = pd.read_csv(io.BytesIO(raw))
        except Exception:
            continue
        x.columns = [c.strip().lower() for c in x.columns]
        tc = next((c for c in x.columns if "time" in c), None)
        rc = next((c for c in x.columns if "rate" in c), None)
        if tc and rc:
            parts.append(x[[tc, rc]].rename(columns={tc: "t", rc: "rate"}))
    if not parts:
        return pd.Series(dtype=float)
    z = pd.concat(parts, ignore_index=True)
    tv = pd.to_numeric(z["t"], errors="coerce")
    z["t"] = pd.to_datetime(tv, unit="us" if tv.max() > 1e15 else "ms", utc=True)
    z = z.dropna(subset=["t"]).drop_duplicates("t").set_index("t").sort_index()
    s = pd.to_numeric(z["rate"], errors="coerce").dropna()
    s.index = s.index.tz_localize(None)
    return s


def main():
    rng = np.random.default_rng(SEED)
    b = pd.read_csv(HERE / "basket_membership.csv", sep=";")
    w = pd.read_csv(HERE / "weekly_spreads.csv", sep=";")
    b["entry"] = pd.to_datetime(b["rebalance_date"])
    b["exit"] = b["entry"] + pd.Timedelta(days=HOLDING_DAYS)

    print(f"[NET] позиций: {len(b)}, недель: {len(w)}")
    print(f"[NET] издержка на ногу: {COST_PER_LEG_PCT:.3f}% "
          f"(комиссия {SIDES_PER_LEG}×{TAKER_FEE_PCT}% + "
          f"слиппедж {SIDES_PER_LEG}×{SLIPPAGE_PCT}% [допущение])")

    # ── funding по позициям ──────────────────────────────────────────────────
    print("[NET] загрузка funding...")
    cache, f_sum, f_miss = {}, [], []
    for sym, g in b.groupby("symbol"):
        if sym not in cache:
            cache[sym] = load_funding(sym)
        s = cache[sym]
        for i, r in g.iterrows():
            if s.empty:
                f_sum.append((i, np.nan)); f_miss.append((i, 1)); continue
            win = s.loc[(s.index >= r["entry"]) & (s.index < r["exit"])]
            # окно должно быть ПОКРЫТО данными, а не просто непусто:
            # если ряд начинается/кончается внутри недели — покрытие частичное
            covered = (not win.empty and s.index.min() <= r["entry"]
                       and s.index.max() >= r["exit"] - pd.Timedelta(hours=8))
            if covered:
                f_sum.append((i, float(win.sum()) * 100))   # доли → %
                f_miss.append((i, 0))
            else:
                f_sum.append((i, np.nan)); f_miss.append((i, 1))
    b["funding_pct"] = pd.Series(dict(f_sum))
    b["funding_missing"] = pd.Series(dict(f_miss))

    cov = 1 - b.funding_missing.mean()
    print(f"[NET] funding покрыт: {int((b.funding_missing == 0).sum())}/{len(b)} "
          f"позиций ({cov*100:.1f}%)")

    b.to_csv(HERE / "basket_membership_net.csv", sep=";", index=False)

    # ── недельная агрегация ──────────────────────────────────────────────────
    rows = []
    for d, g in b.groupby("rebalance_date"):
        L, S = g[g.side == "LONG"], g[g.side == "SHORT"]
        if L.empty or S.empty:
            continue
        cL = cS = COST_PER_LEG_PCT
        gross = L["return"].mean() - S["return"].mean()
        net_fs = gross - cL - cS
        # funding: лонг платит, шорт получает
        fl_ok = int(L.funding_missing.sum()) == 0
        fs_ok = int(S.funding_missing.sum()) == 0
        if fl_ok and fs_ok:
            fL, fS = L.funding_pct.mean(), S.funding_pct.mean()
            net_all = net_fs - fL + fS
        else:
            fL = fS = net_all = np.nan
        rows.append({
            "rebalance_date": d,
            "n_long": len(L), "n_short": len(S),
            "long_mean": round(L["return"].mean(), 4),
            "short_mean": round(S["return"].mean(), 4),
            "spread_gross": round(gross, 4),
            "costs_long": round(cL, 4), "costs_short": round(cS, 4),
            "spread_net": round(net_fs, 4),
            "funding_long_pct": round(fL, 5) if fl_ok else np.nan,
            "funding_short_pct": round(fS, 5) if fs_ok else np.nan,
            "spread_net_with_funding": round(net_all, 4) if fl_ok and fs_ok else np.nan,
            "funding_coverage_pct": round((1 - g.funding_missing.mean()) * 100, 1),
        })
    nw = pd.DataFrame(rows).sort_values("rebalance_date").reset_index(drop=True)
    nw.to_csv(HERE / "weekly_spreads_net.csv", sep=";", index=False)

    # ── тесты ────────────────────────────────────────────────────────────────
    def perm(df, col_l="LONG", col_s="SHORT", cost=0.0, fund=False):
        """Permutation внутри недели с теми же издержками на перемешанных корзинах."""
        weeks = []
        for d, g in b.groupby("rebalance_date"):
            if fund and (g.funding_missing.sum() > 0):
                continue
            r = g["return"].to_numpy()
            fnd = g["funding_pct"].to_numpy() if fund else None
            nl = int((g.side == "LONG").sum()); ns = int((g.side == "SHORT").sum())
            if nl and ns:
                weeks.append((r, fnd, nl, ns))
        if not weeks:
            return np.nan
        def stat(shuffle):
            v = []
            for r, fnd, nl, ns in weeks:
                idx = np.random.default_rng(rng.integers(1 << 31)).permutation(len(r)) \
                      if shuffle else np.arange(len(r))
                rr = r[idx]
                s = rr[:nl].mean() - rr[nl:nl+ns].mean() - 2 * COST_PER_LEG_PCT
                if fund:
                    ff = fnd[idx]
                    s += -ff[:nl].mean() + ff[nl:nl+ns].mean()
                v.append(s)
            return float(np.mean(v))
        obs = stat(False)
        cnt = sum(abs(stat(True)) >= abs(obs) for _ in range(N_PERMUTATION))
        return (cnt + 1) / (N_PERMUTATION + 1)

    def block(series, label, p_perm):
        x = series.dropna().to_numpy()
        lo, hi = bootstrap_ci(x, rng)
        ps = sign_flip(x, rng)
        return {
            "series": label, "n_weeks": len(x),
            "mean_pct": round(float(x.mean()), 4),
            "median_pct": round(float(np.median(x)), 4),
            "weeks_pos_pct": round(float((x > 0).mean() * 100), 1),
            "std_pp": round(float(x.std()), 3),
            "boot_ci_lo": round(lo, 4), "boot_ci_hi": round(hi, 4),
            "boot_excl_0": int(lo > 0 or hi < 0),
            "p_sign_flip": round(ps, 4),
            "p_permutation": round(p_perm, 4) if not np.isnan(p_perm) else np.nan,
        }

    print("[NET] тесты...")
    res = [
        block(nw.spread_gross, "GROSS (headline Step 3)", np.nan),
        block(nw.spread_net, "NET комиссии+слиппедж (вся история)", perm(nw)),
    ]
    sub = nw.dropna(subset=["spread_net_with_funding"])
    if len(sub) >= 10:
        res.append(block(sub.spread_net_with_funding,
                         "NET +funding (только покрытые недели)",
                         perm(nw, fund=True)))
        res.append(block(sub.spread_gross,
                         "  ├ gross на тех же неделях", np.nan))
        res.append(block(sub.spread_net,
                         "  └ net без funding на тех же неделях", np.nan))
    rdf = pd.DataFrame(res)
    rdf.to_csv(HERE / "net_of_costs_summary.csv", sep=";", index=False)

    print("\n" + "=" * 100)
    print(f"{'ряд':<42}{'нед':>5}{'mean':>9}{'median':>9}{'>0':>7}"
          f"{'CI95':>22}{'p_sign':>8}{'p_perm':>8}")
    print("-" * 100)
    for _, r in rdf.iterrows():
        pp = "  н/д " if pd.isna(r.p_permutation) else f"{r.p_permutation:8.4f}"
        print(f"{r['series']:<42}{r.n_weeks:>5}{r.mean_pct:>+9.3f}"
              f"{r.median_pct:>+9.3f}{r.weeks_pos_pct:>6.1f}%"
              f"  [{r.boot_ci_lo:+7.3f}..{r.boot_ci_hi:+7.3f}]"
              f"{r.p_sign_flip:>8.4f}{pp}")

    g0 = float(nw.spread_gross.mean()); n0 = float(nw.spread_net.mean())
    print(f"\n  издержки съедают: {g0-n0:.3f} пп из {g0:+.3f}% = "
          f"{(g0-n0)/abs(g0)*100:.1f}% валового спреда")
    print(f"  остаётся: {n0:+.3f}%/нед")

    write_md(nw, rdf, cov, sub, b_ref=b)
    print(f"\n→ RESULT_net_of_costs.md, weekly_spreads_net.csv, "
          f"net_of_costs_summary.csv, basket_membership_net.csv")
    return nw, rdf


def write_md(nw, rdf, cov, sub, b_ref=None):
    g0 = float(nw.spread_gross.mean()); n0 = float(nw.spread_net.mean())
    gm = float(nw.spread_gross.median()); nm = float(nw.spread_net.median())
    r_net = rdf[rdf.series.str.startswith("NET комиссии")].iloc[0]
    n_sig = int(r_net.boot_excl_0) + int(r_net.p_sign_flip < 0.05) + \
            int(r_net.p_permutation < 0.05 if pd.notna(r_net.p_permutation) else 0)

    L = []; A = L.append
    A("# Lab 06 Step 3 — спред NET OF COSTS\n\n")
    A(f"**Дата:** {pd.Timestamp.now().date().isoformat()}\n\n")
    A("Методология ranking / корзин / holding period **не менялась**. "
      "Использованы уже посчитанные `weekly_spreads.csv` и "
      "`basket_membership.csv`; заново ничего не сортировалось.\n")

    A("\n## Модель издержек\n\n")
    A("| компонент | значение | статус |\n|---|---|---|\n")
    A(f"| комиссия taker | **{TAKER_FEE_PCT}%** за сторону | Binance USDⓈ-M, "
      f"VIP 0, без BNB-скидки |\n")
    A(f"| сторон на ногу | {SIDES_PER_LEG} (вход + выход) | — |\n")
    A(f"| слиппедж | **{SLIPPAGE_PCT}%** за сторону | **ДОПУЩЕНИЕ**, не измерение |\n")
    A(f"| **итого на ногу** | **{COST_PER_LEG_PCT:.2f}%** за неделю | — |\n")
    A(f"| **на обе ноги** | **{2*COST_PER_LEG_PCT:.2f} пп** за неделю | вычитается из спреда |\n")
    A(f"| funding | реальные ставки за период удержания | лонг платит, шорт получает |\n")

    A("\nВзят **taker**, а не maker: momentum-ребалансировка требует входа по "
      "рынку в момент открытия недели, лимитное исполнение не гарантировано. "
      "Maker-комиссия дала бы более благоприятную картину, но не отражала бы "
      "механику стратегии.\n")
    A(f"\nСлиппедж {SLIPPAGE_PCT}% за сторону — **допущение**. Реальная величина "
      f"зависит от размера позиции и состояния стакана в конкретный момент; "
      f"ни того, ни другого в данных нет. Число не подбиралось под результат.\n")

    A("\n## Покрытие funding — определяющее ограничение\n\n")
    A(f"Источник funding — `lab_03_bot1_oi_funding_price_divergence/data/funding/`. "
      f"Эти архивы качались под задачи Lab 03 и покрывают лишь **2025-10 … 2026-05** "
      f"по 372 символам, тогда как Step 3 идёт с 2020-02 по 2026-07 по 752 символам.\n\n")
    A(f"| | |\n|---|---|\n")
    A(f"| позиций всего | {len(pd.read_csv(HERE/'basket_membership.csv',sep=';'))} |\n")
    A(f"| **funding покрыт** | **{cov*100:.1f}% позиций** |\n")
    A(f"| недель всего | {len(nw)} |\n")
    A(f"| **недель с полным покрытием funding** | **{len(sub)}** |\n")

    A("\n**Ноль вместо отсутствующего funding не подставлялся.** Подстановка "
      "нуля означала бы утверждение «funding был нулевым», которого данные не "
      "подтверждают, и систематически занижала бы издержки. Позиции без "
      "данных помечены `funding_missing=1` в `basket_membership_net.csv`.\n")
    A("\nОтсюда два слоя результата — это следствие покрытия, а не выбор:\n")
    A(f"- **Слой A** — net of комиссии + слиппедж, вся история ({len(nw)} недель, "
      f"100% позиций). Комиссии и слиппедж не зависят от внешних данных.\n")
    A(f"- **Слой B** — net of комиссии + слиппедж + funding, только "
      f"{len(sub)} недель с полным покрытием.\n")

    A("\n## Результат\n\n")
    A("| ряд | недель | mean | median | недель >0 | bootstrap CI95 | CI≠0 | "
      "p sign-flip | p permutation |\n|---|---|---|---|---|---|---|---|---|\n")
    for _, r in rdf.iterrows():
        pp = "н/д" if pd.isna(r.p_permutation) else f"{r.p_permutation:.4f}"
        A(f"| {r['series']} | {r.n_weeks} | **{r.mean_pct:+.3f}%** | "
          f"{r.median_pct:+.3f}% | {r.weeks_pos_pct:.1f}% | "
          f"[{r.boot_ci_lo:+.3f} .. {r.boot_ci_hi:+.3f}] | "
          f"{'да' if r.boot_excl_0 else 'нет'} | {r.p_sign_flip:.4f} | {pp} |\n")

    A(f"\n### Сколько съедают издержки\n\n")
    A(f"- валовый спред (headline): **{g0:+.3f}%**/нед\n")
    A(f"- издержки комиссии+слиппедж: **{2*COST_PER_LEG_PCT:.2f} пп**/нед\n")
    A(f"- чистый спред: **{n0:+.3f}%**/нед\n")
    A(f"- **съедено: {g0-n0:.3f} пп = {(g0-n0)/abs(g0)*100:.1f}% валового спреда**\n")
    A(f"- по медиане: {gm:+.3f}% → {nm:+.3f}%\n")

    if len(sub):
        sg = float(sub.spread_gross.mean()); sn = float(sub.spread_net.mean())
        sf = float(sub.spread_net_with_funding.mean())
        A(f"\n### Вклад funding (на {len(sub)} покрытых неделях)\n\n")
        A(f"- gross на этих неделях: {sg:+.3f}%\n")
        A(f"- net без funding: {sn:+.3f}%\n")
        A(f"- net с funding: **{sf:+.3f}%**\n")
        A(f"- вклад funding: **{sf-sn:+.3f} пп**\n\n")
        A(f"Выборка в {len(sub)} недель статистически слаба и покрывает один "
          f"короткий отрезок рынка — читать как оценку порядка величины, не как "
          f"самостоятельный результат.\n")
    else:
        A("\n### Вклад funding НЕ ИЗМЕРЕН\n\n")
        A(f"**Ни одной недели с полным покрытием funding не нашлось.** "
          f"Максимальное покрытие внутри недели — "
          f"{float(nw.funding_coverage_pct.max()):.1f}%, недель с покрытием "
          f"выше нуля — {int((nw.funding_coverage_pct > 0).sum())} из {len(nw)}.\n\n")
        A("Причина в том, что корзины Step 3 набираются из всей вселенной "
          "(752 символа), а funding есть только по 372 символам Lab 03 и только "
          "за 8 месяцев. В типичной неделе внутри окна дат покрыта примерно "
          "половина корзины.\n\n")
        A("Посчитать недельный funding по половине корзины было бы **скрытой "
          "подстановкой**: среднее по покрытой половине неявно распространилось "
          "бы на непокрытую. Поэтому слой B пуст, а не заполнен приблизительно.\n\n")
        A("**Что это значит для вердикта:** вклад funding в чистый спред "
          "остаётся НЕИЗМЕРЕННЫМ, а не нулевым. Он может как улучшить, так и "
          "ухудшить результат слоя A.\n")
        cov_pos = b_ref[b_ref.funding_missing == 0] if b_ref is not None else None
        if cov_pos is not None and len(cov_pos):
            fl = cov_pos[cov_pos.side == "LONG"].funding_pct
            fs = cov_pos[cov_pos.side == "SHORT"].funding_pct
            if len(fl) and len(fs):
                eff = -fl.mean() + fs.mean()
                A(f"\nЕдинственное, что можно сказать по покрытым **позициям** "
                  f"(не неделям, {len(cov_pos)} шт.): средний funding за период "
                  f"удержания составил {fl.mean():+.4f}% у лонг-ноги и "
                  f"{fs.mean():+.4f}% у шорт-ноги. Если бы эти величины были "
                  f"репрезентативны для всей истории, вклад в спред составил бы "
                  f"около **{eff:+.4f} пп** — на фоне издержек "
                  f"{2*COST_PER_LEG_PCT:.2f} пп это второй порядок. "
                  f"Это **ориентир по направлению**, а не оценка: выборка "
                  f"смещена и по символам, и по периоду.\n")

    A("\n## Вердикт по гейту PLAN.md\n\n")
    if n0 < 0 and r_net.median_pct < 0:
        v = ("Спред после издержек **устойчиво отрицателен** — и по среднему, "
             "и по медиане.")
        act = "**ЗАКРЫТЬ реализацию.**"
    elif n0 > 0 and n_sig >= 1:
        v = (f"Спред после издержек **остаётся положительным** "
             f"({n0:+.3f}%/нед) и проходит {n_sig} из 3 тестов значимости.")
        act = "**ПЕРЕДАТЬ ДАЛЬШЕ на holdout.**"
    elif n0 > 0:
        v = (f"Спред после издержек остаётся положительным ({n0:+.3f}%/нед), "
             f"но не проходит ни одного теста значимости.")
        act = ("**Уходит в шум.** Это результат, а не ошибка: издержки съели "
               "эффект до неотличимого от нуля.")
    else:
        v = f"Спред после издержек отрицателен по среднему ({n0:+.3f}%/нед)."
        act = "**Уходит в отрицательное.** Фиксируется честно как результат."
    A(f"{v}\n\n{act}\n")
    A(f"\nОговорка: вердикт опирается на **слой A** (комиссии + слиппедж, вся "
      f"история, {len(nw)} недель, 100% позиций). Funding в него не входит: "
      f"покрытие {cov*100:.1f}% позиций и НОЛЬ недель с полным покрытием — "
      f"измерить его вклад на этих данных нельзя (см. раздел выше). "
      f"Он остаётся неизмеренным, а не нулевым.\n")
    A("\nФормулировки «доказано» / «опровергнуто» не используются: это гейт-"
      "решение о продолжении работы, а не утверждение об эффекте.\n")

    A("\n## Файлы\n")
    A("- `net_of_costs.py` — расчёт\n")
    A("- `weekly_spreads_net.csv` — понедельно: gross, costs_long/short, "
      "spread_net, funding, покрытие\n")
    A("- `basket_membership_net.csv` — позиции с `funding_pct` и `funding_missing`\n")
    A("- `net_of_costs_summary.csv` — сводка тестов\n")

    (HERE / "RESULT_net_of_costs.md").write_text("".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
