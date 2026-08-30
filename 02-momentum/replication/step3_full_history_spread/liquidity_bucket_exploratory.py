#!/usr/bin/env python3
"""
Lab 06 — EXPLORATORY / POST-HOC: momentum-спред по группам ликвидности.

╔══════════════════════════════════════════════════════════════════════════╗
║  СТАТУС: EXPLORATORY / POST-HOC — ГЕНЕРАЦИЯ ГИПОТЕЗЫ, НЕ ПОДТВЕРЖДЕНИЕ.  ║
║                                                                          ║
║  Этот тест придуман ПОСЛЕ просмотра слабого headline Step 3 (+0.573%).   ║
║  По определению это post-hoc: любой результат здесь — гипотеза, которую  ║
║  нужно проверять отдельно на holdout, а не вывод.                        ║
║  Ни при каком исходе не писать «эффект подтверждён».                     ║
╚══════════════════════════════════════════════════════════════════════════╝

ЗАЧЕМ. В презентации Yukun Liu (Nov 2019, слайд 20) momentum значим только
у крупных монет (5-1 спред +4.2%/нед, t=2.83), у мелких незначим
(-1.1%/нед, t=-0.56). Проверяем, воспроизводится ли похожая ФОРМА на нашей
Binance-панели.

ВАЖНО ПРО ПРОКСИ. Мы группируем по quote_volume (ОБОРОТ), а у Liu группировка
по market cap (КАПИТАЛИЗАЦИЯ). Это разные величины: монета может иметь высокий
оборот при скромной капитализации и наоборот. Капитализации в наших данных
нет физически (klines её не содержат). Поэтому это НЕ репликация их среза,
а проверка родственной по духу гипотезы на доступном прокси.

МЕТОДОЛОГИЯ СОРТИРОВКИ НЕ МЕНЯЕТСЯ. Momentum-окно, holding period, веса,
календарь, обработка пропусков — всё импортируется из full_history_spread.py
и переиспользуется как есть. Меняется ровно одно: вселенная каждой недели
дополнительно делится на группы по ликвидности, и спред считается внутри
каждой группы отдельно.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# Переиспользуем headline-методологию, а не изобретаем заново
from full_history_spread import (          # noqa: E402
    MOMENTUM_LOOKBACK_DAYS, HOLDING_DAYS,
    LIQUIDITY_LOOKBACK_DAYS, MIN_LIQUIDITY_USDT, MIN_LIQUIDITY_OBS,
    N_QUANTILES, N_BOOTSTRAP, N_SIGNFLIP, N_PERMUTATION, SEED,
    load_panels, at, bootstrap_ci, sign_flip,
)

# ═════════════════════════════════════════════════════════════════════════════
# ПАРАМЕТРЫ ЭТОГО СРЕЗА — зафиксированы ДО просмотра результата по группам
# ═════════════════════════════════════════════════════════════════════════════
# 5 групп, границы — квинтили trailing 30d median quote_volume СРЕДИ символов,
# прошедших headline-фильтр $1M. Квинтили выбраны потому, что это объективное
# разбиение по самим данным, не подогнанное под исход: границы пересчитываются
# каждую неделю из фактического распределения оборота, а не задаются числом,
# которое можно было бы подобрать.
N_LIQ_GROUPS = 5

# Минимум монет в группе-неделе, чтобы вообще формировать корзины.
# Взято ТО ЖЕ правило, что в headline (`n_elig < N_QUANTILES * 2 → пропуск`),
# а не новое число — чтобы не вводить ещё одну степень свободы.
MIN_COINS_PER_GROUP = N_QUANTILES * 2

LIQ_LABELS = {1: "L1 (самый низкий оборот)", 2: "L2", 3: "L3", 4: "L4",
              5: "L5 (самый высокий оборот)"}


def build_weeks_by_liquidity(op, cl, vol):
    """
    Тот же недельный цикл, что в headline, с одним отличием: вселенная
    делится на N_LIQ_GROUPS групп по обороту, и momentum-сортировка
    выполняется ВНУТРИ каждой группы.
    """
    idx = cl.index
    panel_end = idx.max()
    mondays = [d for d in idx if d.dayofweek == 0]

    rows = []
    for entry_ts in mondays:
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
        if int(eligible.sum()) < N_LIQ_GROUPS * MIN_COINS_PER_GROUP:
            continue

        syms = eligible[eligible].index
        mom = (c_rank[syms] / c_prev[syms] - 1) * 100
        liq = liq_med[syms]

        # группы по обороту — квинтили внутри уже отфильтрованной вселенной
        try:
            grp = pd.qcut(liq, N_LIQ_GROUPS, labels=False, duplicates="drop") + 1
        except (ValueError, IndexError):
            continue

        o_exit = at(op, exit_ts)
        win = cl.loc[(cl.index > entry_ts) & (cl.index < exit_ts)]
        beyond_panel = exit_ts > panel_end

        for g in sorted(grp.dropna().unique()):
            gs = grp[grp == g].index
            if len(gs) < MIN_COINS_PER_GROUP:
                continue
            gmom = mom[gs].sort_values(ascending=False)
            k = max(1, len(gs) // N_QUANTILES)
            longs, shorts = list(gmom.index[:k]), list(gmom.index[-k:])

            legs = {"LONG": [], "SHORT": []}
            for side, bucket in (("LONG", longs), ("SHORT", shorts)):
                for s in bucket:
                    e = float(o_entry[s])
                    xp = o_exit[s] if s in o_exit.index else np.nan
                    if pd.isna(xp) or xp <= 0:
                        col = win[s].dropna() if s in win.columns else pd.Series(dtype=float)
                        col = col[col > 0]
                        if col.empty:
                            continue
                        xp = float(col.iloc[-1])
                    legs[side].append((float(xp) / e - 1) * 100)

            L, S = np.array(legs["LONG"]), np.array(legs["SHORT"])
            if len(L) == 0 or len(S) == 0:
                continue
            rows.append({
                "rebalance_date": entry_ts.date().isoformat(),
                "liq_group": int(g),
                "n_group": len(gs),
                "n_long": len(L), "n_short": len(S),
                "liq_min": float(liq[gs].min()), "liq_max": float(liq[gs].max()),
                "liq_median": float(liq[gs].median()),
                "long_mean": round(float(L.mean()), 4),
                "short_mean": round(float(S.mean()), 4),
                "spread_mean": round(float(L.mean() - S.mean()), 4),
                "spread_median": round(float(np.median(L) - np.median(S)), 4),
                "beyond_panel": int(beyond_panel),
                "_L": L.tolist(), "_S": S.tolist(),
            })
    return pd.DataFrame(rows)


def permutation_group(df_g, rng) -> float:
    """
    Тот же тест, что в headline: внутри каждой недели монеты случайно
    перераспределяются между ногами при сохранении размеров корзин.
    Здесь — в пределах одной группы ликвидности.
    """
    weeks = []
    for _, r in df_g.iterrows():
        arr = np.array(r["_L"] + r["_S"], float)
        nl, ns = len(r["_L"]), len(r["_S"])
        if nl and ns:
            weeks.append((arr, nl, ns))
    if not weeks:
        return float("nan")
    obs = float(df_g["spread_mean"].mean())

    def one():
        v = []
        for arr, nl, ns in weeks:
            p = rng.permutation(arr)
            v.append(p[:nl].mean() - p[nl:nl + ns].mean())
        return float(np.mean(v))

    cnt = sum(abs(one()) >= abs(obs) for _ in range(N_PERMUTATION))
    return (cnt + 1) / (N_PERMUTATION + 1)


def main():
    rng = np.random.default_rng(SEED)
    op, cl, vol = load_panels()

    print("\n" + "=" * 78)
    print("EXPLORATORY / POST-HOC — momentum-спред по группам ликвидности")
    print("=" * 78)
    print(f"  групп: {N_LIQ_GROUPS} (квинтили trailing {LIQUIDITY_LOOKBACK_DAYS}d "
          f"median quote_volume среди прошедших фильтр "
          f"${MIN_LIQUIDITY_USDT:,})")
    print(f"  momentum-сортировка внутри группы: квинтили, как в headline")
    print("  прокси ликвидности — ОБОРОТ, не капитализация\n")

    d = build_weeks_by_liquidity(op, cl, vol)
    if d.empty:
        sys.exit("[ERR] нет данных")

    out = []
    for g in sorted(d.liq_group.unique()):
        gd = d[d.liq_group == g]
        sp = gd["spread_mean"].to_numpy()
        lo, hi = bootstrap_ci(sp, rng)
        p_s = sign_flip(sp, rng)
        p_p = permutation_group(gd, rng)
        out.append({
            "liq_group": int(g), "label": LIQ_LABELS.get(int(g), str(g)),
            "n_weeks": len(gd),
            "median_n_group": int(gd.n_group.median()),
            "liq_median_usdt": round(float(gd.liq_median.median()), 0),
            "spread_mean_pct": round(float(sp.mean()), 4),
            "spread_median_pct": round(float(np.median(sp)), 4),
            "weeks_positive_pct": round(float((sp > 0).mean() * 100), 1),
            "std_pp": round(float(sp.std()), 3),
            "boot_ci_lo": round(lo, 4), "boot_ci_hi": round(hi, 4),
            "boot_excludes_0": int(lo > 0 or hi < 0),
            "p_sign_flip": round(p_s, 4),
            "p_permutation": round(p_p, 4),
            "n_significant": int((lo > 0 or hi < 0) + (p_s < 0.05) + (p_p < 0.05)),
        })
    s = pd.DataFrame(out)

    d.drop(columns=["_L", "_S"]).to_csv(HERE / "liquidity_bucket_weekly.csv",
                                        sep=";", index=False)
    s.to_csv(HERE / "liquidity_bucket_summary.csv", sep=";", index=False)

    print(f"{'группа':<26}{'нед':>5}{'монет':>7}{'оборот млн':>12}"
          f"{'mean':>9}{'median':>9}{'>0':>7}{'CI≠0':>6}{'p_sign':>8}{'p_perm':>8}")
    print("-" * 103)
    for _, r in s.iterrows():
        print(f"{r['label']:<26}{r['n_weeks']:>5}{r['median_n_group']:>7}"
              f"{r['liq_median_usdt']/1e6:>12.1f}"
              f"{r['spread_mean_pct']:>+9.3f}{r['spread_median_pct']:>+9.3f}"
              f"{r['weeks_positive_pct']:>6.1f}%"
              f"{'да' if r['boot_excludes_0'] else 'нет':>6}"
              f"{r['p_sign_flip']:>8.4f}{r['p_permutation']:>8.4f}")

    # ── форма ────────────────────────────────────────────────────────────────
    m = s["spread_mean_pct"].to_numpy()
    diffs = np.diff(m)
    sig = s["n_significant"].to_numpy()
    if np.all(diffs > 0):
        shape = "монотонно усиливается с ликвидностью"
    elif np.all(diffs < 0):
        shape = "монотонно ослабевает с ликвидностью"
    elif sig.sum() == 0:
        shape = "формы нет, ни одна группа не значима — шум по подвыборкам"
    elif int(np.argmax(m)) == len(m) - 1 and sig[-1] > 0:
        shape = "работает преимущественно в верхней группе"
    elif int(np.argmax(m)) == 0 and sig[0] > 0:
        shape = "работает преимущественно в нижней группе (обратно гипотезе)"
    else:
        shape = "хаотичен — значимость не выстраивается по ликвидности"

    print(f"\n  ФОРМА: {shape}")
    print(f"  групп со значимостью хотя бы по одному тесту: "
          f"{int((sig > 0).sum())} из {len(s)}")
    print(f"  корреляция ранга группы и спреда: "
          f"{np.corrcoef(s.liq_group, m)[0, 1]:+.3f}")

    write_md(s, d, shape)
    print(f"\n→ RESULT_liquidity_exploratory.md")
    print(f"→ liquidity_bucket_summary.csv, liquidity_bucket_weekly.csv")


def write_md(s, d, shape):
    n_sig = int((s["n_significant"] > 0).sum())
    hdr = ("> ⚠️ **EXPLORATORY / POST-HOC.** Этот срез придуман ПОСЛЕ просмотра "
           "слабого headline Step 3 (+0.573%/нед). По определению это "
           "генерация гипотезы, а не подтверждение. Ни один результат ниже "
           "не является доказательством эффекта.\n")
    L = []
    A = L.append
    A("# Lab 06 — momentum-спред по группам ликвидности (EXPLORATORY)\n\n")
    A(hdr)
    A(f"\n**Дата:** {pd.Timestamp.now().date().isoformat()}\n")

    A("\n## Гипотеза и её источник\n")
    A("Презентация Yukun Liu (Nov 2019, слайд 20): momentum значим только у "
      "крупных монет (5-1 спред +4.2%/нед, t=2.83), у мелких незначим "
      "(−1.1%/нед, t=−0.56). Проверяем, воспроизводится ли похожая **форма**.\n")

    A("\n### Ключевое расхождение с источником гипотезы\n")
    A("У Liu группировка по **капитализации**, у нас — по **обороту** "
      "(`quote_volume`). Это разные величины: монета может иметь высокий "
      "оборот при скромной капитализации и наоборот. Капитализации в наших "
      "данных нет физически — klines её не содержат. Поэтому это **не "
      "репликация их среза**, а проверка родственной по духу гипотезы на "
      "доступном прокси.\n")

    A("\n## Метод\n")
    A(f"- Вся методология сортировки импортирована из "
      f"`full_history_spread.py` и не менялась: momentum "
      f"{MOMENTUM_LOOKBACK_DAYS}d, holding {HOLDING_DAYS}d, entry/exit по "
      f"open понедельника, равные веса, квинтили.\n")
    A(f"- Единственное изменение: вселенная каждой недели делится на "
      f"**{N_LIQ_GROUPS} групп** по trailing {LIQUIDITY_LOOKBACK_DAYS}d median "
      f"`quote_volume`, и momentum-спред считается **внутри каждой группы**.\n")
    A(f"- Границы групп — квинтили фактического распределения оборота среди "
      f"символов, прошедших headline-фильтр ${MIN_LIQUIDITY_USDT:,}. "
      f"Пересчитываются каждую неделю. Число групп и способ разбиения "
      f"зафиксированы **до** просмотра результатов по группам.\n")
    A(f"- Минимум монет в группе-неделе: {MIN_COINS_PER_GROUP} — то же правило, "
      f"что в headline, а не новое число.\n")

    A("\n## Результат по группам\n\n")
    A("| группа | недель | монет в группе | медиана оборота | спред mean | "
      "спред median | недель >0 | bootstrap CI | CI≠0 | p sign-flip | "
      "p permutation |\n")
    A("|---|---|---|---|---|---|---|---|---|---|---|\n")
    for _, r in s.iterrows():
        A(f"| {r['label']} | {r['n_weeks']} | {r['median_n_group']} | "
          f"${r['liq_median_usdt']/1e6:.1f}M | **{r['spread_mean_pct']:+.3f}%** | "
          f"{r['spread_median_pct']:+.3f}% | {r['weeks_positive_pct']:.1f}% | "
          f"[{r['boot_ci_lo']:+.3f} .. {r['boot_ci_hi']:+.3f}] | "
          f"{'да' if r['boot_excludes_0'] else 'нет'} | "
          f"{r['p_sign_flip']:.4f} | {r['p_permutation']:.4f} |\n")

    A(f"\n## Форма\n\n**{shape}**\n\n")
    A(f"- групп со значимостью хотя бы по одному тесту: **{n_sig} из {len(s)}**\n")
    A(f"- корреляция ранга группы и величины спреда: "
      f"{np.corrcoef(s.liq_group, s.spread_mean_pct)[0,1]:+.3f}\n")

    # ── что НЕ сходится с гипотезой ──────────────────────────────────────────
    m = s["spread_mean_pct"].to_numpy()
    md_ = s["spread_median_pct"].to_numpy()
    mono = bool(np.all(np.diff(m) > 0))
    breaks = [(int(s.liq_group.iloc[i]), int(s.liq_group.iloc[i + 1]))
              for i in range(len(m) - 1) if m[i] > m[i + 1]]
    disagree = s[(np.sign(m) != np.sign(md_)) & (m != 0)]
    neg_sig = s[(s.spread_mean_pct < 0) & (s.n_significant > 0)]

    A("\n### Что НЕ сходится с гипотезой\n")
    A("Раздел обязателен: корреляция ранга и спреда сама по себе может "
      "создать впечатление чистого градиента, которого в данных нет.\n\n")

    if mono:
        A("- Спред монотонно растёт с ликвидностью — нарушений порядка нет.\n")
    else:
        pairs = ", ".join(f"L{a}>L{b}" for a, b in breaks)
        A(f"- **Градиент НЕ монотонный.** Порядок нарушается: {pairs}. "
          f"Самая неликвидная группа не является худшей, а значит картина "
          f"«чем ликвиднее, тем лучше» в чистом виде не выполняется.\n")

    if len(disagree):
        A(f"- **Среднее и медиана расходятся по знаку** в группах: "
          f"{', '.join('L'+str(int(g)) for g in disagree.liq_group)}. ")
        for _, r in disagree.iterrows():
            A(f"У L{int(r['liq_group'])} mean {r['spread_mean_pct']:+.3f}%, "
              f"median {r['spread_median_pct']:+.3f}% — ")
        A("положительное среднее держится на хвосте, а типичная неделя "
          "убыточна. По правилу 6 такие группы нельзя читать по среднему.\n")
    else:
        A("- Среднее и медиана согласованы по знаку во всех группах.\n")

    both_pos = s[(s.spread_mean_pct > 0) & (s.spread_median_pct > 0) &
                 (s.n_significant > 0)]
    A(f"- Групп, где **и среднее, и медиана положительны, и есть значимость**: "
      f"**{len(both_pos)}**"
      + (f" ({', '.join('L'+str(int(g)) for g in both_pos.liq_group)})" if len(both_pos) else "")
      + ". Это самый строгий срез — именно он, а не число «значимых» групп, "
        "показывает, где эффект действительно устойчив.\n")

    if len(neg_sig):
        A(f"- **Значимо ОТРИЦАТЕЛЬНЫЕ группы: "
          f"{', '.join('L'+str(int(g)) for g in neg_sig.liq_group)}.** "
          f"Исходная гипотеза предсказывает, что у неликвидных монет эффект "
          f"**незначим**, а не значимо обратный. Значимый разворот — это "
          f"отклонение от гипотезы, а не её подтверждение, и он требует "
          f"отдельного объяснения.\n")

    A("\n## Множественное тестирование — обязательная оговорка\n")
    A(f"Протестировано **{len(s)} групп × 3 теста = {len(s)*3} проверок "
      f"значимости**. При {len(s)} независимых проверках вероятность получить "
      f"p<0.05 хотя бы в одной группе существенно выше 5% даже при полном "
      f"отсутствии эффекта (примерно "
      f"{(1 - 0.95**len(s))*100:.0f}% при независимости).\n\n")
    A("Формальная поправка (Bonferroni и т.п.) намеренно **не применялась** — "
      "это exploratory-срез, а не confirmatory-тест, и поправка создала бы "
      "ложное впечатление строгости.\n\n")
    if n_sig == 1:
        A("**Здесь значимой оказалась ровно одна группа из пяти — это ровно тот "
          "случай, для которого оговорка написана.** Одна значимая группа из "
          "пяти статистически ожидаема и при отсутствии всякого эффекта. "
          "Читать её как находку нельзя.\n")
    elif n_sig == 0:
        A("Ни одна группа не показала значимости — вопрос множественного "
          "тестирования в этом прогоне не возникает.\n")
    else:
        A(f"Значимых групп: {n_sig}. Даже так — при {len(s)*3} проверках часть "
          f"из них ожидаема случайно.\n")

    A("\n## Вывод\n")
    if n_sig == 0:
        A("Гипотеза **не подкреплена** в этом exploratory-срезе: ни в одной "
          "группе ликвидности momentum-спред не отделился от нуля.\n")
    else:
        A(f"Гипотеза **частично подкреплена** в этом exploratory-срезе — "
          f"с учётом оговорок выше.\n\n")
        A(f"Подкрепляет: направление совпадает с источником гипотезы — самая "
          f"ликвидная группа даёт наибольший спред "
          f"({s.spread_mean_pct.iloc[-1]:+.3f}%), корреляция ранга и спреда "
          f"{np.corrcoef(s.liq_group, s.spread_mean_pct)[0,1]:+.3f}.\n\n")
        A(f"Не подкрепляет: градиент немонотонный, часть «значимых» групп "
          f"держится на среднем при отрицательной медиане, и присутствуют "
          f"значимо отрицательные группы, чего гипотеза не предсказывает "
          f"(см. раздел «Что НЕ сходится с гипотезой»).\n")
    A("\nВ любом случае требуется **отдельная проверка на holdout**: границы "
      "групп, число групп и сам вопрос выбраны после просмотра headline, и "
      "никакой результат этого среза не может считаться подтверждением.\n")

    A("\n## Файлы\n")
    A("- `liquidity_bucket_exploratory.py` — расчёт\n")
    A("- `liquidity_bucket_summary.csv` — сводка по группам\n")
    A("- `liquidity_bucket_weekly.csv` — понедельно × группа\n")

    A("\n---\n\n")
    A("> ⚠️ **EXPLORATORY / POST-HOC.** Повторно: срез придуман после "
      "просмотра headline. Результат — гипотеза для проверки на независимых "
      "данных, не вывод. Headline Step 3 и его методология этим срезом не "
      "меняются.\n")

    (HERE / "RESULT_liquidity_exploratory.md").write_text("".join(L),
                                                          encoding="utf-8")


if __name__ == "__main__":
    main()
