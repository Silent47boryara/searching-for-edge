#!/usr/bin/env python3
"""
Lab 06 — cross-sectional momentum spread на полной истории.

(Поправка нумерации: папка называется step3_ по порядку файлов внутри Lab 06.
 По 6-этапной дорожной карте это всё ещё Этап 2 — вторая половина.
 Funding, комиссии и слиппедж НЕ учитываются: это Этап 3 роадмапа.)

ЦЕЛЬ: максимально близко воспроизвести классическую cross-sectional
momentum-логику на торгуемой Binance Futures-вселенной. Не изобретать
собственную версию стратегии. Отклонения от методологии допустимы только
ради исполнимости данных (forced close при делистинге) и описаны явно —
не оптимизированы по результату.

Источник данных исключительно локальный. Сеть не используется.
"""

# ═════════════════════════════════════════════════════════════════════════════
# ПРЕ-РЕГИСТРАЦИЯ МЕТОДОЛОГИИ
#
# Всё ниже зафиксировано ДО просмотра результата. После просмотра — не менять.
# Sensitivity-таблица и outlier/jackknife ниже — ДОПОЛНИТЕЛЬНЫЕ диагностики
# поверх этого headline, они его не отменяют и не заменяют.
# ═════════════════════════════════════════════════════════════════════════════

# ── Календарь сделки ─────────────────────────────────────────────────────────
# Ranking date = close воскресенья (последняя завершённая дневная свеча
#                перед понедельником)
# Entry        = open понедельника
# Exit         = open следующего понедельника
# Открытие-в-открытие на обоих концах. Смешивать open на входе с close на
# выходе нельзя — это внесло бы асимметричное искажение.
MOMENTUM_LOOKBACK_DAYS = 7    # trailing momentum: 7 календарных дней до ranking date
HOLDING_DAYS           = 7    # entry понедельник → exit следующий понедельник

# Все lookback-окна заканчиваются строго ДО entry.
# Цена entry (open понедельника) НИКОГДА не участвует в расчёте momentum.

# ── Фильтр ликвидности (headline) ────────────────────────────────────────────
# Абсолютный порог в USDT по trailing 30-дневному МЕДИАННОМУ дневному обороту.
#
# Почему абсолютный, а не дециль: дециль относителен к размеру вселенной и
# плывёт вместе с рынком. В 2020 при ~50 монетах и в 2026 при ~800 «нижний
# дециль» — это пороги разного смысла, и вселенная менялась бы вместе с
# рынком, а не по единому критерию исполнимости.
#
# Почему именно 1 000 000 USDT — выбрано от исполнимости позиции, НЕ по
# лучшему историческому результату (результат на момент выбора не смотрелся):
# при медианном дневном обороте $1M позиция $10k составляет 1% дневного
# объёма — общепринятый ориентир, при котором воздействие на цену остаётся
# умеренным. При корзине примерно в сотню монет на ногу это соответствует
# ноге около $1M, то есть осмысленному размеру портфеля.
LIQUIDITY_LOOKBACK_DAYS = 30
MIN_LIQUIDITY_USDT      = 1_000_000

# Минимум наблюдений в 30-дневном окне, чтобы медиана оборота вообще имела
# смысл. Без этого монета с двумя торговыми днями получила бы «медиану»
# по двум точкам. Порог объявлен здесь, а не подобран по результату.
MIN_LIQUIDITY_OBS = 20

# ── Формирование корзин ──────────────────────────────────────────────────────
N_QUANTILES = 5     # квинтили: верхний = Long, нижний = Short
# Веса внутри ноги равные.

# ── Диагностика (НЕ headline) ────────────────────────────────────────────────
# Альтернативные пороги ликвидности заданы заранее, вместе с headline.
# Служат только для оценки чувствительности и НЕ являются основанием
# менять headline после просмотра результата.
SENSITIVITY_THRESHOLDS = [0, 250_000, 5_000_000]
PARTIAL_SLICE_FROM     = "2023-01-01"   # отдельный срез, помечается PARTIAL
TOP_OUTLIER_WEEKS      = 5

# ── Статистика ───────────────────────────────────────────────────────────────
# Единица наблюдения — НЕДЕЛЯ. Bootstrap ресемплирует недели, sign-flip меняет
# знак недельного спреда, permutation внутри каждой недели перераспределяет
# монеты между ногами с сохранением размеров корзин.
N_BOOTSTRAP   = 10_000
N_SIGNFLIP    = 10_000
N_PERMUTATION = 5_000
SEED          = 42

# ═════════════════════════════════════════════════════════════════════════════

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE  = Path(__file__).resolve().parent
PANEL_DIR = HERE.parent / "step2_multiyear_klines"

P_OPEN  = PANEL_DIR / "panel_open.csv"
P_CLOSE = PANEL_DIR / "panel_close.csv"
P_VOL   = PANEL_DIR / "panel_quote_volume.csv"


# ─────────────────────────────────────────────────────────────────────────────
# Загрузка
# ─────────────────────────────────────────────────────────────────────────────
def load_panels() -> tuple:
    missing = [p.name for p in (P_OPEN, P_CLOSE, P_VOL) if not p.exists()]
    if missing:
        raise SystemExit(
            f"[ERR] нет входных файлов: {', '.join(missing)}\n"
            f"      каталог: {PANEL_DIR}\n"
            f"      Сначала выполните в step2_multiyear_klines:\n"
            f"        python3 download_multiyear_klines.py\n"
            f"        python3 build_panel.py   (должен создать panel_open.csv)\n"
        )

    def rd(p: Path) -> pd.DataFrame:
        d = pd.read_csv(p, sep=";", index_col=0, parse_dates=True)
        return d.sort_index()

    op, cl, vol = rd(P_OPEN), rd(P_CLOSE), rd(P_VOL)

    # Выравнивание по общей сетке. Панели строятся build_panel.py на одной
    # сетке, но выравниваем явно — расхождение формы молча исказило бы всё.
    idx = cl.index
    cols = cl.columns
    op = op.reindex(index=idx, columns=cols)
    vol = vol.reindex(index=idx, columns=cols)

    print(f"[DATA] панель: {cl.shape[0]} дней × {cl.shape[1]} символов")
    print(f"[DATA] период: {idx.min().date()} → {idx.max().date()}")
    print(f"[DATA] непустых: close={int(cl.notna().sum().sum())}  "
          f"open={int(op.notna().sum().sum())}  "
          f"quote_volume={int(vol.notna().sum().sum())}")
    return op, cl, vol


def at(df: pd.DataFrame, ts: pd.Timestamp) -> pd.Series:
    """Строка панели на точную дату; пустая серия, если даты нет."""
    if ts in df.index:
        return df.loc[ts]
    return pd.Series(np.nan, index=df.columns)


# ─────────────────────────────────────────────────────────────────────────────
# Построение недельных корзин
# ─────────────────────────────────────────────────────────────────────────────
def build_weeks(op: pd.DataFrame, cl: pd.DataFrame, vol: pd.DataFrame,
                min_liquidity: float) -> tuple:
    """
    Возвращает (members_df, weekly_df, unexecutable_df).

    members_df — одна строка на символ в неделю (только Long/Short корзины).
    weekly_df  — одна строка на неделю ребалансировки.
    unexecutable — позиции, где после entry в окне удержания нет ни одной цены.
    """
    idx = cl.index
    panel_end = idx.max()
    mondays = [d for d in idx if d.dayofweek == 0]

    members, weekly, unexec = [], [], []

    for entry_ts in mondays:
        exit_ts = entry_ts + pd.Timedelta(days=HOLDING_DAYS)
        rank_ts = entry_ts - pd.Timedelta(days=1)                    # воскресенье
        mom_ts  = rank_ts - pd.Timedelta(days=MOMENTUM_LOOKBACK_DAYS)

        # ── momentum: строго по данным ДО entry ──────────────────────────────
        c_rank = at(cl, rank_ts)
        c_prev = at(cl, mom_ts)
        ok_mom = c_rank.notna() & c_prev.notna() & (c_prev > 0) & (c_rank > 0)

        # ── ликвидность: окно заканчивается на ranking date ──────────────────
        liq_win = vol.loc[(vol.index > rank_ts - pd.Timedelta(
            days=LIQUIDITY_LOOKBACK_DAYS)) & (vol.index <= rank_ts)]
        liq_obs = liq_win.notna().sum()
        liq_med = liq_win.median(skipna=True)
        ok_liq = (liq_obs >= MIN_LIQUIDITY_OBS) & liq_med.notna() & \
                 (liq_med >= min_liquidity)

        # ── entry: open понедельника обязателен ──────────────────────────────
        # Если open входного понедельника отсутствует — символ не включается.
        # Брать следующую доступную цену нельзя: это сдвинуло бы вход вперёд
        # уже с знанием того, что произошло дальше.
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
        # Цены для forced close: всё строго ПОСЛЕ entry и ДО планового exit.
        win = cl.loc[(cl.index > entry_ts) & (cl.index < exit_ts)]

        # Причина forced close различается принципиально:
        #   panel_end       — данные кончились, exit-понедельника ещё не было.
        #                     Затрагивает ВСЕ позиции недели одновременно и
        #                     ничего не говорит о рынке — это край выборки.
        #   missing_exit    — цены нет у конкретного символа (делистинг, пауза
        #                     торгов). Именно ради этого случая правило и введено.
        # Смешивать их в одном счётчике нельзя: первое механическое, второе
        # содержательное. Методология при этом не меняется — обе обрабатываются
        # одинаково, различается только пометка и отчётность.
        beyond_panel = exit_ts > panel_end

        leg_rets = {"LONG": [], "SHORT": []}
        for side, bucket in (("LONG", longs), ("SHORT", shorts)):
            for s in bucket:
                entry_px = float(o_entry[s])
                forced = 0
                forced_reason = ""
                exit_px = o_exit[s] if s in o_exit.index else np.nan

                if pd.isna(exit_px) or exit_px <= 0:
                    # Планового open на exit нет → forced close по последней
                    # доступной цене внутри окна удержания.
                    col = win[s].dropna() if s in win.columns else pd.Series(dtype=float)
                    col = col[col > 0]
                    if col.empty:
                        # Ни одной цены после entry — позиция неисполнима.
                        # Не NaN и не молчаливое удаление: учитывается отдельно.
                        unexec.append({
                            "rebalance_date": entry_ts.date().isoformat(),
                            "symbol": s, "side": side,
                            "entry_price": entry_px,
                            "momentum_7d": round(float(mom[s]), 4),
                            "reason": "no_price_after_entry",
                        })
                        continue
                    exit_px = float(col.iloc[-1])
                    forced = 1
                    forced_reason = "panel_end" if beyond_panel else "missing_exit"
                else:
                    exit_px = float(exit_px)

                ret = (exit_px / entry_px - 1) * 100
                leg_rets[side].append(ret)
                members.append({
                    "rebalance_date": entry_ts.date().isoformat(),
                    "symbol": s, "side": side,
                    "momentum_7d": round(float(mom[s]), 4),
                    "liquidity_30d_median": round(float(liq_med[s]), 2),
                    "entry_price": entry_px,
                    "exit_price": exit_px,
                    "return": round(ret, 4),
                    "forced_close_flag": forced,
                    "forced_reason": forced_reason,
                })

        L, S = np.array(leg_rets["LONG"]), np.array(leg_rets["SHORT"])
        if len(L) == 0 or len(S) == 0:
            continue

        weekly.append({
            "rebalance_date": entry_ts.date().isoformat(),
            "exit_date": exit_ts.date().isoformat(),
            "n_universe": n_elig,
            "n_long": len(L), "n_short": len(S),
            "long_mean": round(float(L.mean()), 4),
            "short_mean": round(float(S.mean()), 4),
            "long_median": round(float(np.median(L)), 4),
            "short_median": round(float(np.median(S)), 4),
            "spread_mean": round(float(L.mean() - S.mean()), 4),
            "spread_median": round(float(np.median(L) - np.median(S)), 4),
        })

    return (pd.DataFrame(members), pd.DataFrame(weekly),
            pd.DataFrame(unexec))


# ─────────────────────────────────────────────────────────────────────────────
# Статистические тесты — единица наблюдения НЕДЕЛЯ
# ─────────────────────────────────────────────────────────────────────────────
def bootstrap_ci(spreads: np.ndarray, rng) -> tuple:
    """CI95 среднего недельного спреда. Ресемплируются НЕДЕЛИ, не монеты."""
    n = len(spreads)
    means = np.array([spreads[rng.integers(0, n, n)].mean()
                      for _ in range(N_BOOTSTRAP)])
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def sign_flip(spreads: np.ndarray, rng) -> float:
    """H0: знак недельного спреда случаен. Прямо учитывает малое N по времени."""
    obs = abs(spreads.mean())
    n = len(spreads)
    cnt = sum(abs((spreads * rng.choice([-1, 1], n)).mean()) >= obs
              for _ in range(N_SIGNFLIP))
    return (cnt + 1) / (N_SIGNFLIP + 1)


def permutation_within_week(members: pd.DataFrame, weekly: pd.DataFrame,
                            rng) -> float:
    """
    H0: momentum-ранжирование не отличается от случайного отбора монет
    ВНУТРИ той же недели при тех же размерах корзин.

    Полностью контролирует общий крипто-бета: сравнение идёт не с нулём,
    а со случайными корзинами той же недели.
    """
    weeks = []
    for d, g in members.groupby("rebalance_date"):
        r = g["return"].to_numpy()
        nl = int((g["side"] == "LONG").sum())
        ns = int((g["side"] == "SHORT").sum())
        if nl and ns and len(r) >= nl + ns:
            weeks.append((r, nl, ns))
    if not weeks:
        return float("nan")

    obs = float(weekly["spread_mean"].mean())

    def one() -> float:
        vals = []
        for r, nl, ns in weeks:
            p = rng.permutation(r)
            vals.append(p[:nl].mean() - p[nl:nl + ns].mean())
        return float(np.mean(vals))

    cnt = sum(abs(one()) >= abs(obs) for _ in range(N_PERMUTATION))
    return (cnt + 1) / (N_PERMUTATION + 1)


# ─────────────────────────────────────────────────────────────────────────────
# Отчёт
# ─────────────────────────────────────────────────────────────────────────────
def fmt_p(p: float) -> str:
    if np.isnan(p):
        return "н/д"
    mark = "ЗНАЧИМО" if p < 0.05 else ("гранично" if p < 0.10 else "НЕ значимо")
    return f"p={p:.4f}  {mark}"


def main() -> None:
    rng = np.random.default_rng(SEED)
    op, cl, vol = load_panels()

    print(f"\n[HEADLINE] порог ликвидности: "
          f"{MIN_LIQUIDITY_USDT:,} USDT (trailing {LIQUIDITY_LOOKBACK_DAYS}d median)")
    print("[HEADLINE] расчёт недельных корзин...")
    members, weekly, unexec = build_weeks(op, cl, vol, MIN_LIQUIDITY_USDT)

    if weekly.empty:
        raise SystemExit("[ERR] не получено ни одной валидной недели")

    sp = weekly["spread_mean"].to_numpy()
    n_weeks = len(weekly)

    # ── тесты ────────────────────────────────────────────────────────────────
    print(f"[HEADLINE] недель: {n_weeks}. Статистические тесты...")
    ci_lo, ci_hi = bootstrap_ci(sp, rng)
    p_sign = sign_flip(sp, rng)
    p_perm = permutation_within_week(members, weekly, rng)

    # ── forced closures ──────────────────────────────────────────────────────
    forced = members[members["forced_close_flag"] == 1].copy()
    n_forced = len(forced)
    forced_by_side = forced["side"].value_counts().to_dict() if n_forced else {}
    forced_by_reason = (forced["forced_reason"].value_counts().to_dict()
                        if n_forced else {})
    n_panel_end = int(forced_by_reason.get("panel_end", 0))
    n_missing_exit = int(forced_by_reason.get("missing_exit", 0))

    # Вклад forced close в итог: сравнение headline с версией, где forced-строки
    # исключены (пересчёт недельных средних по оставшимся позициям).
    if n_forced:
        clean = members[members["forced_close_flag"] == 0]
        rows = []
        for d, g in clean.groupby("rebalance_date"):
            L = g[g.side == "LONG"]["return"]
            S = g[g.side == "SHORT"]["return"]
            if len(L) and len(S):
                rows.append(L.mean() - S.mean())
        spread_wo_forced = float(np.mean(rows)) if rows else float("nan")
    else:
        spread_wo_forced = float(sp.mean())

    # ── диагностика: outlier / jackknife ─────────────────────────────────────
    w = weekly.copy()
    top = w.reindex(w["spread_mean"].abs().sort_values(ascending=False).index)
    wo_top = w.drop(top.head(TOP_OUTLIER_WEEKS).index)["spread_mean"].mean()
    jack = np.array([np.delete(sp, i).mean() for i in range(n_weeks)])

    # ── диагностика: sensitivity по порогам ──────────────────────────────────
    print("[ДИАГНОСТИКА] sensitivity по альтернативным порогам ликвидности...")
    sens = [{
        "threshold_usdt": MIN_LIQUIDITY_USDT, "is_headline": 1,
        "n_weeks": n_weeks,
        "median_universe": int(weekly["n_universe"].median()),
        "spread_mean_pct": round(float(sp.mean()), 4),
        "spread_median_pct": round(float(np.median(sp)), 4),
        "weeks_positive": int((sp > 0).sum()),
    }]
    for thr in SENSITIVITY_THRESHOLDS:
        _m, _w, _u = build_weeks(op, cl, vol, thr)
        if _w.empty:
            continue
        s2 = _w["spread_mean"].to_numpy()
        sens.append({
            "threshold_usdt": thr, "is_headline": 0,
            "n_weeks": len(_w),
            "median_universe": int(_w["n_universe"].median()),
            "spread_mean_pct": round(float(s2.mean()), 4),
            "spread_median_pct": round(float(np.median(s2)), 4),
            "weeks_positive": int((s2 > 0).sum()),
        })
    sens_df = pd.DataFrame(sens)

    # ── диагностика: срез 2023+ (PARTIAL) ────────────────────────────────────
    recent = weekly[weekly["rebalance_date"] >= PARTIAL_SLICE_FROM]
    r_sp = recent["spread_mean"].to_numpy() if len(recent) else np.array([])

    # ── артефакты ────────────────────────────────────────────────────────────
    weekly.to_csv(HERE / "weekly_spreads.csv", sep=";", index=False)
    members.to_csv(HERE / "basket_membership.csv", sep=";", index=False)
    forced_out = forced if n_forced else pd.DataFrame(
        columns=["rebalance_date", "symbol", "side", "momentum_7d",
                 "liquidity_30d_median", "entry_price", "exit_price",
                 "return", "forced_close_flag"])
    if not unexec.empty:
        forced_out = pd.concat([forced_out, unexec], ignore_index=True)
    forced_out.to_csv(HERE / "forced_closures.csv", sep=";", index=False)
    sens_df.to_csv(HERE / "liquidity_sensitivity.csv", sep=";", index=False)

    write_result_md(
        weekly=weekly, members=members, sp=sp, n_weeks=n_weeks,
        ci=(ci_lo, ci_hi), p_sign=p_sign, p_perm=p_perm,
        n_forced=n_forced, forced_by_side=forced_by_side,
        n_panel_end=n_panel_end, n_missing_exit=n_missing_exit,
        spread_wo_forced=spread_wo_forced, n_unexec=len(unexec),
        top=top, wo_top=wo_top, jack=jack, sens_df=sens_df,
        recent=recent, r_sp=r_sp, cl=cl,
    )

    # ── консоль ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 78)
    print("HEADLINE — вся история, без tier-гейтов")
    print("=" * 78)
    print(f"  недель: {n_weeks}   период: {weekly['rebalance_date'].iloc[0]} → "
          f"{weekly['rebalance_date'].iloc[-1]}")
    print(f"  вселенная после фильтра: {weekly['n_universe'].min()}.."
          f"{weekly['n_universe'].max()} (медиана "
          f"{int(weekly['n_universe'].median())})")
    print(f"\n  LONG   mean={weekly['long_mean'].mean():+7.3f}%   "
          f"median={weekly['long_median'].median():+7.3f}%")
    print(f"  SHORT  mean={weekly['short_mean'].mean():+7.3f}%   "
          f"median={weekly['short_median'].median():+7.3f}%")
    print(f"  СПРЕД  mean={sp.mean():+7.3f}%   median={np.median(sp):+7.3f}%")
    print(f"  недель со спредом > 0: {int((sp > 0).sum())}/{n_weeks} "
          f"({(sp > 0).mean() * 100:.1f}%)   ст.откл.={sp.std():.3f} пп")
    print(f"\n  bootstrap CI95 : [{ci_lo:+.3f}% .. {ci_hi:+.3f}%]  "
          f"{'НЕ накрывает 0' if (ci_lo > 0 or ci_hi < 0) else 'накрывает 0'}")
    print(f"  sign-flip      : {fmt_p(p_sign)}")
    print(f"  permutation    : {fmt_p(p_perm)}")
    print(f"\n  forced closures: {n_forced} ({forced_by_side})")
    print(f"    missing_exit (делистинг/пауза): {n_missing_exit}")
    print(f"    panel_end (край выборки)      : {n_panel_end}")
    print(f"  неисполнимых позиций: {len(unexec)}")
    print(f"  спред без forced-строк: {spread_wo_forced:+.3f}% "
          f"(headline {sp.mean():+.3f}%)")
    print(f"\n→ RESULT.md, weekly_spreads.csv, basket_membership.csv,")
    print(f"  forced_closures.csv, liquidity_sensitivity.csv")


def write_result_md(**k) -> None:
    weekly = k["weekly"]; members = k["members"]; sp = k["sp"]
    n_weeks = k["n_weeks"]; ci_lo, ci_hi = k["ci"]
    top = k["top"]; jack = k["jack"]; sens_df = k["sens_df"]
    recent = k["recent"]; r_sp = k["r_sp"]; cl = k["cl"]

    L = weekly["long_mean"].mean(); S = weekly["short_mean"].mean()
    Lm = weekly["long_median"].median(); Sm = weekly["short_median"].median()
    pos = int((sp > 0).sum())

    def sig(p):
        return "значимо" if p < 0.05 else ("гранично" if p < 0.10 else "не значимо")

    md = []
    A = md.append
    A("# Lab 06 — cross-sectional momentum spread, полная история\n")
    A("**Класс:** отдельная система (не Signal Context, не Market Regime), "
      "не привязана к `signal_tier`.\n")
    A("**Статус:** Этап 2 роадмапа, вторая половина. Funding, комиссии и "
      "слиппедж НЕ учтены — это Этап 3, отдельно.\n")
    A(f"**Дата расчёта:** {pd.Timestamp.now().date().isoformat()}\n")

    A("\n## Источник\n")
    A(f"Локальные панели `step2_multiyear_klines/`: `panel_open.csv`, "
      f"`panel_close.csv`, `panel_quote_volume.csv`.\n")
    A(f"Панель: {cl.shape[0]} дней × {cl.shape[1]} символов, "
      f"{cl.index.min().date()} → {cl.index.max().date()}. Сеть не использовалась.\n")

    A("\n## Пре-регистрированная методология\n")
    A("Зафиксирована в константах в начале скрипта ДО просмотра результата.\n\n")
    A("| параметр | значение |\n|---|---|\n")
    A(f"| ranking date | close воскресенья (последняя завершённая свеча до понедельника) |\n")
    A(f"| trailing momentum | {MOMENTUM_LOOKBACK_DAYS} календарных дней до ranking date |\n")
    A(f"| entry | open понедельника |\n")
    A(f"| exit | open следующего понедельника ({HOLDING_DAYS} дней) |\n")
    A(f"| корзины | квинтили ({N_QUANTILES}), верхний Long / нижний Short, равные веса |\n")
    A(f"| **порог ликвидности (headline)** | **{MIN_LIQUIDITY_USDT:,} USDT** |\n")
    A(f"| окно ликвидности | trailing {LIQUIDITY_LOOKBACK_DAYS}d median дневного оборота |\n")
    A(f"| мин. наблюдений в окне ликвидности | {MIN_LIQUIDITY_OBS} из {LIQUIDITY_LOOKBACK_DAYS} |\n")

    A("\n**Порог ликвидности выбран от исполнимости позиции, не по лучшему "
      "историческому результату.** При медианном дневном обороте $1M позиция "
      "$10k составляет 1% дневного объёма — ориентир, при котором воздействие "
      "на цену остаётся умеренным. При корзине около сотни монет на ногу это "
      "нога примерно $1M.\n")
    A("\n**Отсутствие look-ahead.** Все lookback-окна заканчиваются строго до "
      "entry; цена entry (open понедельника) никогда не участвует в расчёте "
      "momentum.\n")

    A("\n## Результат headline (вся история, без гейтов)\n")
    A(f"- недель: **{n_weeks}**, период {weekly['rebalance_date'].iloc[0]} → "
      f"{weekly['rebalance_date'].iloc[-1]}\n")
    A(f"- вселенная после фильтра: {weekly['n_universe'].min()}–"
      f"{weekly['n_universe'].max()}, медиана "
      f"{int(weekly['n_universe'].median())}\n\n")
    A("| нога | mean по неделям | median по неделям |\n|---|---|---|\n")
    A(f"| LONG (верхний квинтиль) | {L:+.3f}% | {Lm:+.3f}% |\n")
    A(f"| SHORT (нижний квинтиль) | {S:+.3f}% | {Sm:+.3f}% |\n")
    A(f"| **СПРЕД (Long − Short)** | **{sp.mean():+.3f}%** | "
      f"**{np.median(sp):+.3f}%** |\n")
    A(f"\n- недель со спредом > 0: **{pos}/{n_weeks}** "
      f"({pos / n_weeks * 100:.1f}%)\n")
    A(f"- стандартное отклонение недельного спреда: {sp.std():.3f} пп\n")
    A(f"- квартили: {np.percentile(sp, [0, 25, 50, 75, 100]).round(3).tolist()}\n")
    A("\nМедиана приведена рядом со средним по правилу 6 — средние без медианы "
      "не публикуются.\n")

    A("\n### Значимость (единица наблюдения — неделя)\n")
    A("| тест | результат |\n|---|---|\n")
    A(f"| bootstrap CI95 (ресемплинг недель) | [{ci_lo:+.3f}% .. {ci_hi:+.3f}%] — "
      f"{'НЕ накрывает 0' if (ci_lo > 0 or ci_hi < 0) else 'накрывает 0'} |\n")
    A(f"| sign-flip по неделям | p={k['p_sign']:.4f} — {sig(k['p_sign'])} |\n")
    A(f"| permutation внутри недели | p={k['p_perm']:.4f} — {sig(k['p_perm'])} |\n")
    A("\nPermutation перераспределяет монеты между ногами внутри той же недели "
      "с сохранением размеров корзин: сравнение идёт не с нулём, а со "
      "случайными корзинами той же недели, что снимает общий крипто-бета.\n")

    A("\n## Обработка пропусков и forced closures\n")
    A("Правила зафиксированы заранее:\n\n")
    A("- **нет open на entry-понедельник** → символ не включается в корзину "
      "этой недели; следующая доступная цена НЕ берётся;\n")
    A("- **нет open на exit-понедельник** → forced close по последней "
      "доступной цене строго после entry и до планового exit;\n")
    A("- **после entry нет ни одной цены** → позиция помечается неисполнимой "
      "и учитывается отдельно, не удаляется молча и не превращается в NaN.\n\n")
    A(f"| | |\n|---|---|\n")
    A(f"| forced closures | **{k['n_forced']}** из {len(members)} позиций |\n")
    A(f"| распределение по ногам | {k['forced_by_side'] or '—'} |\n")
    A(f"| — из них `missing_exit` (делистинг/пауза торгов) | **{k['n_missing_exit']}** |\n")
    A(f"| — из них `panel_end` (край выборки) | {k['n_panel_end']} |\n")
    A(f"| неисполнимых позиций | {k['n_unexec']} |\n")
    A(f"| спред без forced-строк | {k['spread_wo_forced']:+.3f}% "
      f"(headline {sp.mean():+.3f}%) |\n")
    A(f"\nВклад forced close в итог: "
      f"{k['spread_wo_forced'] - sp.mean():+.3f} пп.\n")
    A("\n**Две причины forced close разделены — они разного класса.**\n")
    A("`missing_exit` — цены нет у конкретного символа (делистинг, пауза "
      "торгов). Именно ради этого случая правило и введено, и именно он "
      "содержателен.\n")
    A("`panel_end` — данные кончились, exit-понедельника ещё не наступило. "
      "Затрагивает **все** позиции последней недели одновременно, срезает ей "
      "период удержания и о рынке не говорит ничего. Это край выборки, а не "
      "рыночное событие.\n")
    if k["n_panel_end"]:
        A(f"\nЗдесь `panel_end` дал {k['n_panel_end']} позиций — вся последняя "
          f"неделя. При интерпретации её стоит держать отдельно: холдинг у неё "
          f"короче {HOLDING_DAYS} дней, и с остальными неделями она "
          f"несопоставима.\n")
    A("\nПолный список — `forced_closures.csv` (колонка `forced_reason`).\n")

    A("\n## Диагностика (НЕ headline)\n")
    A("Ниже — дополнительные проверки поверх зафиксированного headline. "
      "Они его не отменяют и не заменяют.\n")

    A(f"\n### Outlier / jackknife\n")
    A(f"Топ-{TOP_OUTLIER_WEEKS} недель по |спреду|:\n\n")
    A("| неделя | спред | long | short | вселенная |\n|---|---|---|---|---|\n")
    for _, r in top.head(TOP_OUTLIER_WEEKS).iterrows():
        A(f"| {r['rebalance_date']} | {r['spread_mean']:+.3f}% | "
          f"{r['long_mean']:+.2f}% | {r['short_mean']:+.2f}% | "
          f"{int(r['n_universe'])} |\n")
    A(f"\n- headline без топ-{TOP_OUTLIER_WEEKS} недель: "
      f"**{k['wo_top']:+.3f}%** (полный {sp.mean():+.3f}%)\n")
    A(f"- jackknife по одной неделе: от {jack.min():+.3f}% до {jack.max():+.3f}%\n")
    A(f"- знак спреда стабилен при удалении любой недели: "
      f"**{'да' if (jack.min() > 0) == (jack.max() > 0) else 'нет'}**\n")

    A("\n### Sensitivity по порогу ликвидности\n")
    A("**Диагностика, не основание менять headline.** Пороги заданы заранее, "
      "вместе с headline.\n\n")
    A("| порог USDT | headline | недель | медиана вселенной | спред mean | "
      "спред median | недель > 0 |\n|---|---|---|---|---|---|---|\n")
    for _, r in sens_df.iterrows():
        A(f"| {int(r['threshold_usdt']):,} | "
          f"{'**да**' if r['is_headline'] else 'нет'} | {int(r['n_weeks'])} | "
          f"{int(r['median_universe'])} | {r['spread_mean_pct']:+.3f}% | "
          f"{r['spread_median_pct']:+.3f}% | {int(r['weeks_positive'])} |\n")

    A(f"\n### Срез {PARTIAL_SLICE_FROM}+ — PARTIAL\n")
    if len(r_sp):
        A(f"Недель: {len(recent)}. Спред mean **{r_sp.mean():+.3f}%**, "
          f"median {np.median(r_sp):+.3f}%, недель > 0: "
          f"{int((r_sp > 0).sum())}/{len(r_sp)}.\n")
    else:
        A("Недостаточно недель в срезе.\n")
    A("\n**PARTIAL: срез не заменяет headline.** Он короче, статистически "
      "слабее и выбран по календарю, а не по критерию — читать как "
      "иллюстрацию, не как результат.\n")

    A("\n## Обязательные фиксации\n")
    A("\n### 1. Доступность short-контракта на дату входа\n")
    A("Гарантирована источником данных. Панель построена из "
      "`futures/um/klines`: если цена присутствует на дату входа, значит "
      "перпетуал в этот день физически торговался. Дополнительная проверка "
      "не выполнялась и не требуется.\n")
    A("\n### 2. Фильтр ликвидности против умирающих монет\n")
    A("Монета перед делистингом обычно теряет оборот постепенно и может "
      "выпасть из вселенной по порогу ликвидности **ещё до** реального "
      "делистинга — то есть именно в момент, когда её движение было бы самым "
      "информативным для шорт-ноги.\n\n")
    A("Это известный компромисс между «реалистично исполнимо» и «ловит самое "
      "информативное движение», тот же класс эффекта, что уже отмечен в "
      "gate-check (универсум может систематически разворачивать momentum). "
      "Не ошибка методологии, но оговорка обязательная: шорт-нога здесь "
      "заведомо консервативнее, чем была бы без фильтра.\n")

    A("\n## Вердикт\n")
    A("_Заполняется после просмотра результата._ Планка гейта — из PLAN.md, "
      "раздел Lab 06: явная поломка (устойчиво обратный знак) → закрыть эту "
      "реализацию, не гипотезу; шум → «недостаточно данных»; спред есть и не "
      "держится на 1–2 неделях → Этап 3 роадмапа (издержки и robustness).\n")

    A("\n## Файлы\n")
    A("- `full_history_spread.py` — расчёт\n")
    A("- `weekly_spreads.csv` — по неделям: ноги, спред, размер вселенной\n")
    A("- `basket_membership.csv` — символ × неделя: сторона, momentum, "
      "ликвидность, цены, доходность, forced-флаг\n")
    A("- `forced_closures.csv` — вынужденные закрытия и неисполнимые позиции\n")
    A("- `liquidity_sensitivity.csv` — таблица чувствительности\n")

    (HERE / "RESULT.md").write_text("".join(md), encoding="utf-8")


if __name__ == "__main__":
    main()
