"""
Lab 06 — Cross-Sectional Momentum Rotation (GATE CHECK).

ЭТО НЕ ПОЛНАЯ СИСТЕМА. Самый грубый прогон, чтобы понять, стоит ли копать
глубже. Издержки НЕ учитываются (следующий шаг, если гейт пройден).

ВОПРОС: существует ли на нашей вселенной монет и в наш период кросс-секционный
momentum-спред — топ-дециль по trailing 7d доходности против нижнего дециля,
с горизонтом удержания 7 дней?

Источник идеи — академический (Liu-Tsyvinski-Wu 2022 JoF). Эффект подтверждён
НЕ нами, на десятках тысяч монет и многолетних периодах. Наши ~28 недель
статистически маломощны и физически не могут опровергнуть многолетний результат.
См. правку гейта в PLAN.md от 05.08: "шум" != "опровергнуто".

Данные: уже скачанные 5m перп-klines из Lab 03. Докачки нет.
Ребалансировка: ПОНЕДЕЛЬНИК (зафиксировано).

Look-ahead отсутствует: momentum считается по данным ДО момента ребалансировки
(closes t-7d..t), forward-доходность — строго после (t..t+7d).
"""

import io
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

LAB     = Path(__file__).parent
KLINES  = Path("<local Klines project path>/CMC_гипотезы/"
               "lab_03_bot1_oi_funding_price_divergence/data/klines")
# NOTE: this points at Lab 03's raw klines cache, which is not part of this
# public repo. This gate-check script is included for methodological
# transparency (see gate_check_RESULT.md); the headline replication used in
# the published note is step2/step3/step4, which download their own data
# directly from the public data.binance.vision archive.

LOOKBACK_D  = 7          # trailing momentum window
HOLD_D      = 7          # forward holding period
REBAL_DOW   = 0          # 0 = понедельник
NPERM       = 5000
SEED        = 42
MIN_COINS_PER_BUCKET = 10   # если дециль даёт меньше — переходим на квинтиль
MIN_UNIVERSE = 20           # неделя игнорируется, если монет меньше

KCOLS = ["open_time", "open", "high", "low", "close", "volume", "close_time",
         "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume",
         "ignore"]


def daily_closes(sym_dir: Path) -> pd.Series:
    """Дневные закрытия из 5m-свечей: последняя свеча UTC-суток."""
    parts = []
    for f in sorted(sym_dir.glob("*.zip")):
        try:
            with zipfile.ZipFile(f) as z:
                raw = z.read(z.namelist()[0])
        except Exception:
            continue
        if not raw:
            continue
        first = raw.split(b"\n", 1)[0].split(b",")[0].strip()
        has_hdr = not first.replace(b".", b"", 1).isdigit()
        try:
            d = (pd.read_csv(io.BytesIO(raw)) if has_hdr
                 else pd.read_csv(io.BytesIO(raw), header=None, names=KCOLS))
        except Exception:
            continue
        d.columns = [str(c).strip().lower() for c in d.columns]
        if "open_time" not in d.columns or "close" not in d.columns:
            continue
        parts.append(d[["open_time", "close"]])
    if not parts:
        return pd.Series(dtype=float)

    k = pd.concat(parts, ignore_index=True)
    k["open_time"] = pd.to_numeric(k["open_time"], errors="coerce")
    k = k.dropna(subset=["open_time"])
    if k.empty:
        return pd.Series(dtype=float)
    unit = "us" if k["open_time"].max() > 1e15 else "ms"
    k["t"] = pd.to_datetime(k["open_time"], unit=unit, utc=True)
    k["close"] = pd.to_numeric(k["close"], errors="coerce")
    k = k.dropna(subset=["close"]).drop_duplicates("t").set_index("t").sort_index()
    return k["close"].resample("1D").last().dropna()


def build_price_panel() -> pd.DataFrame:
    cache = LAB / "daily_closes.csv"
    if cache.exists():
        p = pd.read_csv(cache, sep=";", index_col=0, parse_dates=True)
        print(f"[LAB06] дневные закрытия из кэша: {p.shape[0]} дней × "
              f"{p.shape[1]} символов")
        return p

    dirs = sorted([d for d in KLINES.iterdir() if d.is_dir()])
    print(f"[LAB06] строю дневные закрытия из 5m по {len(dirs)} символам...")
    series = {}
    for i, d in enumerate(dirs, 1):
        s = daily_closes(d)
        if len(s) >= LOOKBACK_D + HOLD_D + 1:
            series[d.name] = s
        if i % 50 == 0:
            print(f"  ...{i}/{len(dirs)}  принято={len(series)}", flush=True)

    panel = pd.DataFrame(series).sort_index()
    panel.index = panel.index.tz_localize(None)
    panel.to_csv(cache, sep=";")
    print(f"[LAB06] панель: {panel.shape[0]} дней × {panel.shape[1]} символов "
          f"→ {cache}")
    return panel


def build_weeks(panel: pd.DataFrame, use_quintile: bool):
    """
    На каждый понедельник: momentum (t-7d → t), forward (t → t+7d),
    кросс-секционный ранг, назначение в корзины.
    Возвращает long-format DataFrame: одна строка = монета в неделю.
    """
    q = 5 if use_quintile else 10
    idx = panel.index
    mondays = [d for d in idx if d.dayofweek == REBAL_DOW]

    rows = []
    for t in mondays:
        t_pre = t - pd.Timedelta(days=LOOKBACK_D)
        t_fwd = t + pd.Timedelta(days=HOLD_D)
        if t_pre not in idx or t_fwd not in idx:
            continue

        p_pre, p_now, p_fwd = panel.loc[t_pre], panel.loc[t], panel.loc[t_fwd]
        ok = p_pre.notna() & p_now.notna() & p_fwd.notna() & \
             (p_pre > 0) & (p_now > 0) & (p_fwd > 0)
        if ok.sum() < MIN_UNIVERSE:
            continue

        mom = (p_now[ok] / p_pre[ok] - 1) * 100        # предиктор: строго до t
        fwd = (p_fwd[ok] / p_now[ok] - 1) * 100        # исход: строго после t

        n = len(mom)
        k = max(1, n // q)
        order = mom.sort_values(ascending=False)
        longs, shorts = set(order.index[:k]), set(order.index[-k:])

        for sym in mom.index:
            leg = "LONG" if sym in longs else ("SHORT" if sym in shorts else "MID")
            rows.append({"week": t.date().isoformat(), "symbol": sym,
                         "n_universe": n, "bucket_size": k,
                         "mom_pct": round(float(mom[sym]), 4),
                         "fwd_pct": round(float(fwd[sym]), 4), "leg": leg})
    return pd.DataFrame(rows)


def weekly_spreads(d: pd.DataFrame) -> pd.DataFrame:
    """Спред на неделю: равновзвешенная лонг-корзина минус шорт-корзина."""
    out = []
    for w, g in d.groupby("week"):
        L = g[g.leg == "LONG"]["fwd_pct"]
        S = g[g.leg == "SHORT"]["fwd_pct"]
        M = g[g.leg == "MID"]["fwd_pct"]
        if L.empty or S.empty:
            continue
        out.append({"week": w, "n_universe": int(g.n_universe.iloc[0]),
                    "bucket_size": int(g.bucket_size.iloc[0]),
                    "long_mean": round(L.mean(), 4), "short_mean": round(S.mean(), 4),
                    "long_median": round(L.median(), 4),
                    "short_median": round(S.median(), 4),
                    "mid_mean": round(M.mean(), 4) if not M.empty else np.nan,
                    "spread_mean": round(L.mean() - S.mean(), 4),
                    "spread_median": round(L.median() - S.median(), 4)})
    return pd.DataFrame(out).sort_values("week").reset_index(drop=True)


def perm_within_week(d: pd.DataFrame, rng) -> tuple:
    """
    ГЛАВНЫЙ ТЕСТ. Внутри каждой недели тасуются forward-доходности между
    монетами — momentum-ранжирование заменяется случайным отбором из ТОЙ ЖЕ
    недели. Полностью контролирует общий крипто-бета: сравниваем не с нулём,
    а со случайной корзиной той же недели.
    """
    weeks = [g for _, g in d.groupby("week") if
             (g.leg == "LONG").any() and (g.leg == "SHORT").any()]
    if not weeks:
        return np.nan, np.nan

    def spread_of(frames, shuffled=False):
        vals = []
        for g in frames:
            f = rng.permutation(g["fwd_pct"].values) if shuffled else g["fwd_pct"].values
            legs = g["leg"].values
            L = f[legs == "LONG"]
            S = f[legs == "SHORT"]
            if len(L) and len(S):
                vals.append(L.mean() - S.mean())
        return float(np.mean(vals)) if vals else np.nan

    obs = spread_of(weeks)
    cnt = sum(abs(spread_of(weeks, True)) >= abs(obs) for _ in range(NPERM))
    return obs, (cnt + 1) / (NPERM + 1)


def sign_flip_test(spreads: np.ndarray, rng) -> tuple:
    """
    Тест на уровне НЕДЕЛЬ (единица наблюдения = неделя, N ≈ 28).
    Под нулём знак недельного спреда случаен. Прямо учитывает малое N по времени.
    """
    obs = float(np.mean(spreads))
    n = len(spreads)
    cnt = sum(abs(np.mean(spreads * rng.choice([-1, 1], n))) >= abs(obs)
              for _ in range(NPERM))
    return obs, (cnt + 1) / (NPERM + 1)


def main():
    rng = np.random.default_rng(SEED)
    panel = build_price_panel()
    if panel.empty:
        sys.exit("[ERR] пустая панель")

    print(f"[LAB06] период: {panel.index.min().date()} → {panel.index.max().date()}")

    # ── выбор корзины: дециль или квинтиль ────────────────────────────────────
    dec = build_weeks(panel, use_quintile=False)
    dec_w = weekly_spreads(dec)
    min_dec = int(dec_w.bucket_size.min()) if not dec_w.empty else 0
    use_quint = min_dec < MIN_COINS_PER_BUCKET
    print(f"[LAB06] дециль: минимальный размер корзины по неделям = {min_dec} "
          f"→ {'ПЕРЕХОД НА КВИНТИЛЬ' if use_quint else 'дециль годится'}")

    d = build_weeks(panel, use_quintile=True) if use_quint else dec
    wk = weekly_spreads(d) if use_quint else dec_w
    bucket_label = "квинтиль" if use_quint else "дециль"

    if wk.empty:
        sys.exit("[ERR] нет валидных недель")

    d.to_csv(LAB / "lab_06_weekly_legs.csv", sep=";", index=False)
    wk.to_csv(LAB / "lab_06_weekly_spreads.csv", sep=";", index=False)

    print("\n" + "=" * 76)
    print(f"HEADLINE — вся история, все монеты, без тир-гейта  ({bucket_label})")
    print("=" * 76)
    print(f"  независимых недель (периодов ребалансировки): {len(wk)}")
    print(f"  вселенная монет: {wk.n_universe.min()}..{wk.n_universe.max()} "
          f"(медиана {int(wk.n_universe.median())})")
    print(f"  размер корзины : {wk.bucket_size.min()}..{wk.bucket_size.max()}")
    print(f"  период         : {wk.week.min()} → {wk.week.max()}")

    print(f"\n  средняя недельная доходность ног (7d, БЕЗ издержек):")
    print(f"    LONG  (топ-{bucket_label})   mean={wk.long_mean.mean():+7.3f}%  "
          f"median по неделям={wk.long_mean.median():+7.3f}%")
    print(f"    SHORT (низ-{bucket_label})   mean={wk.short_mean.mean():+7.3f}%  "
          f"median по неделям={wk.short_mean.median():+7.3f}%")
    if wk.mid_mean.notna().any():
        print(f"    MID   (середина)      mean={wk.mid_mean.mean():+7.3f}%")
    print(f"    СПРЕД (long − short)  mean={wk.spread_mean.mean():+7.3f}%  "
          f"median={wk.spread_mean.median():+7.3f}%")
    pos = (wk.spread_mean > 0).sum()
    print(f"    недель со спредом > 0: {pos}/{len(wk)} ({pos / len(wk) * 100:.1f}%)")
    print(f"    ст.откл. недельного спреда: {wk.spread_mean.std():.3f} пп")

    # ── тесты значимости ──────────────────────────────────────────────────────
    print("\n" + "=" * 76)
    print("ЗНАЧИМОСТЬ")
    print("=" * 76)
    obs1, p1 = perm_within_week(d, rng)
    print(f"\n  1. Внутринедельный permutation (контроль общего крипто-бета)")
    print(f"     H0: momentum-ранжирование не отличается от случайного отбора "
          f"внутри той же недели")
    print(f"     спред={obs1:+.3f}%  p={p1:.4f}  "
          f"{'ЗНАЧИМО' if p1 < 0.05 else ('гранично' if p1 < 0.10 else 'НЕ значимо')}")

    sp = wk.spread_mean.values
    obs2, p2 = sign_flip_test(sp, rng)
    print(f"\n  2. Sign-flip на уровне недель (N={len(sp)} — единица наблюдения неделя)")
    print(f"     H0: знак недельного спреда случаен")
    print(f"     средний спред={obs2:+.3f}%  p={p2:.4f}  "
          f"{'ЗНАЧИМО' if p2 < 0.05 else ('гранично' if p2 < 0.10 else 'НЕ значимо')}")

    boot = [np.mean(rng.choice(sp, len(sp), replace=True)) for _ in range(NPERM)]
    lo, hi = np.percentile(boot, [2.5, 97.5])
    print(f"\n  3. Bootstrap CI95 среднего недельного спреда: "
          f"[{lo:+.3f}%..{hi:+.3f}%]  "
          f"{'НЕ накрывает 0' if (lo > 0 or hi < 0) else 'НАКРЫВАЕТ 0'}")

    # ── проверка на outlier (правило 6 / требование гейта) ────────────────────
    print("\n" + "=" * 76)
    print("OUTLIER-ПРОВЕРКА: не держится ли спред на 1-2 экстремальных неделях")
    print("=" * 76)
    top = wk.reindex(wk.spread_mean.abs().sort_values(ascending=False).index)
    print("\n  5 недель с наибольшим |спредом|:")
    for _, r in top.head(5).iterrows():
        print(f"    {r.week}  spread={r.spread_mean:+8.3f}%  "
              f"long={r.long_mean:+7.2f}%  short={r.short_mean:+7.2f}%  "
              f"n={int(r.n_universe)}")
    full = sp.mean()
    for drop in (1, 2, 3):
        kept = wk.drop(top.head(drop).index)
        print(f"\n  без {drop} самых экстремальных недель: "
              f"средний спред={kept.spread_mean.mean():+7.3f}% "
              f"(полный={full:+7.3f}%, недель={len(kept)})")
    jack = [np.mean(np.delete(sp, i)) for i in range(len(sp))]
    print(f"\n  jackknife (удаление по одной неделе): "
          f"min={min(jack):+7.3f}%  max={max(jack):+7.3f}%")
    print(f"  знак спреда стабилен при удалении любой недели: "
          f"{'ДА' if (min(jack) > 0) == (max(jack) > 0) else 'НЕТ'}")

    print("\n  распределение недельных спредов по квартилям:")
    print("   ", np.percentile(sp, [0, 25, 50, 75, 100]).round(3))

    print("\n" + "=" * 76)
    print("НАПОМИНАНИЕ О СТАТУСЕ РЕЗУЛЬТАТА")
    print("=" * 76)
    print(f"  Это GATE CHECK на {len(wk)} независимых недельных периодах.")
    print("  Низкая статистическая мощность: реальный эффект может не показать")
    print("  значимость просто от шума. Отсутствие значимости здесь НЕ является")
    print("  опровержением momentum-фактора, подтверждённого в литературе")
    print("  на многолетних данных. См. правку гейта PLAN.md от 05.08.")
    print("  Издержки (funding, комиссии, слиппедж) НЕ учтены.")

    pd.DataFrame([{
        "weeks": len(wk), "bucket": bucket_label,
        "universe_median": int(wk.n_universe.median()),
        "long_mean_pct": round(wk.long_mean.mean(), 4),
        "short_mean_pct": round(wk.short_mean.mean(), 4),
        "spread_mean_pct": round(float(sp.mean()), 4),
        "spread_median_pct": round(float(np.median(sp)), 4),
        "spread_std_pp": round(float(sp.std()), 4),
        "weeks_positive": int(pos),
        "p_within_week_perm": round(p1, 4),
        "p_sign_flip": round(p2, 4),
        "boot_ci_lo": round(lo, 4), "boot_ci_hi": round(hi, 4),
        "jack_min": round(min(jack), 4), "jack_max": round(max(jack), 4),
    }]).to_csv(LAB / "lab_06_summary.csv", sep=";", index=False)
    print(f"\n→ {LAB / 'lab_06_summary.csv'}")
    print(f"→ {LAB / 'lab_06_weekly_spreads.csv'}")
    print(f"→ {LAB / 'lab_06_weekly_legs.csv'}")


if __name__ == "__main__":
    main()
