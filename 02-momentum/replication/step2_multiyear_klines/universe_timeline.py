#!/usr/bin/env python3
"""
Lab 06, этап 2 — проверка непрерывности покрытия вселенной.

ЗАПУСКАТЬ ПОСЛЕ build_panel.py. Сеть не используется, читает только
локальный panel_close.csv.

ЗАЧЕМ. На этапе 1 (gate check) вселенная скакала ступенями по неделям:
    30 → 318 → 97 → 32 → 45 → 306 → 162
Это был не рынок, а артефакт докачки Lab 03: klines качались только под
месяцы, в которых у символа были сигналы Klines. Из-за этого кросс-секция
в половине недель состояла из почти произвольного подмножества монет,
и результат оказался непригоден.

Этот скрипт — прямая проверка, что новая докачка проблему устранила.

КАК ЧИТАТЬ РЕЗУЛЬТАТ
────────────────────────────────────────────────────────────────────────────
Ожидается ПЛАВНЫЙ рост: Binance листил перпы постепенно, с конца 2019.
Умеренные спады — тоже норма, это делистинги (ради них и качали архив).

Тревожный признак — резкие скачки в разы, особенно ВВЕРХ и ВНИЗ подряд:
такой профиль означает, что покрытие снова определяется наличием файлов,
а не составом рынка. Скрипт помечает такие месяцы флагом `jump_flag`.

Скачки НЕ сглаживаются и НЕ прячутся — при их наличии отчёт этапа 2
должен их зафиксировать, а не замолчать.
"""

from pathlib import Path

import numpy as np
import pandas as pd

HERE     = Path(__file__).resolve().parent
PANEL    = HERE / "panel_close.csv"
COVERAGE = HERE / "panel_coverage.csv"
FAILURES = HERE / "failures.csv"
DELISTED = HERE / "delisted_symbols.json"
OUT      = HERE / "universe_size_timeline.csv"

# ── пороги флагов ────────────────────────────────────────────────────────────
# jump_flag — РАЗМЕР вселенной резко изменился
JUMP_REL   = 0.25   # ±25% от предыдущего месяца
JUMP_ABS   = 20     # и при этом не менее 20 символов в абсолюте

# churn_flag — СОСТАВ вселенной резко сменился, даже если размер почти тот же.
# Это отдельный от jump_flag случай: если за месяц ушло 40 символов и пришло 40,
# n_active не сдвинется, и jump_flag промолчит — а кросс-секция при этом другая.
#
# Почему 50%: в зрелом месяце Binance листит единицы новых перпов на вселенную
# в сотни символов, churn идёт единицами процентов. Смена половины состава за
# месяц рынком не объясняется — это почти наверняка дыра в докачке.
# Почему нужен ещё и абсолютный порог: в начале истории (2019-2020) вселенная
# мала, и появление 5 монет к имеющимся 8 даёт 60% churn совершенно законно.
# Абсолютный порог гасит этот шум, оставляя флаг для настоящих аномалий.
CHURN_REL  = 0.50   # сменилось ≥50% состава относительно прошлого месяца
CHURN_ABS  = 20     # и при этом не менее 20 символов пришло/ушло суммарно

DENSE_FRAC = 0.80   # «торговался весь месяц» = есть цена в ≥80% дней месяца
TOP_GAPS   = 10     # сколько символов показать в топе по длине дыры


def main() -> None:
    if not PANEL.exists():
        raise SystemExit(
            f"[ERR] нет {PANEL}\n"
            f"      Сначала: python download_multiyear_klines.py\n"
            f"      Затем  : python build_panel.py\n"
            f"      И только потом этот скрипт."
        )

    panel = pd.read_csv(PANEL, sep=";", index_col=0, parse_dates=True)
    panel = panel.sort_index()
    print(f"[UNIV] панель: {panel.shape[0]} дней × {panel.shape[1]} символов")
    print(f"[UNIV] период: {panel.index.min().date()} → {panel.index.max().date()}")

    present = panel.notna()
    month = panel.index.to_period("M")

    # активен = есть хотя бы одна цена закрытия в этом месяце
    n_active = present.groupby(month).any().sum(axis=1)

    # Плотное присутствие = цена есть в >=80% КАЛЕНДАРНЫХ дней месяца.
    # Знаменатель берётся из самого периода, а не из числа строк панели за месяц:
    # если в панели вообще нет какой-то даты (ни один символ в тот день не
    # торговался), число строк окажется меньше календарного, и n_dense будет
    # завышен. Совпадать эти величины будут только случайно.
    days_with_price = present.groupby(month).sum()
    periods = days_with_price.index
    days_in_month = pd.Series([p.days_in_month for p in periods], index=periods)
    n_dense = (days_with_price.div(days_in_month, axis=0) >= DENSE_FRAC).sum(axis=1)

    # появления и уходы: символ активен в этом месяце, но не в предыдущем / наоборот
    act = present.groupby(month).any()
    prev = act.shift(1).fillna(False).infer_objects(copy=False)
    n_new  = (act & ~prev).sum(axis=1)
    n_gone = (~act & prev).sum(axis=1)

    # Строк панели за месяц — отдельно от календарного числа дней: расхождение
    # само по себе диагностично (полностью пропущенные даты в панели).
    rows_in_month = present.groupby(month).size()

    df = pd.DataFrame({
        "month": n_active.index.astype(str),
        "n_active": n_active.values,
        "n_dense": n_dense.values,
        "n_new": n_new.values,
        "n_gone": n_gone.values,
        "cal_days": days_in_month.values,
        "panel_rows": rows_in_month.values,
    })
    df["chg"] = df["n_active"].diff()
    df["chg_pct"] = (df["n_active"].pct_change() * 100).round(1)

    # churn: какая доля состава сменилась относительно прошлого месяца
    prev_active = df["n_active"].shift(1)
    df["churn_pct"] = ((df["n_new"] + df["n_gone"]) / prev_active * 100).round(1)

    df["jump_flag"] = (
        (df["chg"].abs() >= JUMP_ABS) &
        (df["chg_pct"].abs() >= JUMP_REL * 100)
    ).astype(int)
    df["churn_flag"] = (
        ((df["n_new"] + df["n_gone"]) >= CHURN_ABS) &
        (df["churn_pct"] >= CHURN_REL * 100)
    ).astype(int)

    # ── месяцы, которые нельзя флагать ───────────────────────────────────────
    # Первый месяц — старт истории: там все символы «новые», churn=100%
    # по построению, а chg не с чем сравнивать.
    # Последний месяц — если докачка оборвана в середине месяца, часть символов
    # выглядит «ушедшей» просто потому, что их файлы ещё не скачаны. Это дало бы
    # ложный скачок ровно на хвосте, где его легче всего принять за настоящий.
    last_ts     = panel.index.max()
    last_period = periods[-1]
    last_partial = last_ts.day < last_period.days_in_month
    df["partial_month"] = 0
    df.loc[0, "partial_month"] = 1
    if last_partial:
        df.loc[df.index[-1], "partial_month"] = 1
    df.loc[df["partial_month"] == 1, ["jump_flag", "churn_flag"]] = 0

    df.to_csv(OUT, sep=";", index=False)

    # ── вывод ────────────────────────────────────────────────────────────────
    mx = int(df["n_active"].max()) or 1
    print("\n" + "=" * 78)
    print("РАЗМЕР ВСЕЛЕННОЙ ПО МЕСЯЦАМ  (n_active = есть цена закрытия в месяце)")
    print("=" * 78)
    for _, r in df.iterrows():
        bar = "#" * int(r["n_active"] / mx * 38)
        marks = []
        if r["jump_flag"]:
            marks.append("СКАЧОК")
        if r["churn_flag"]:
            marks.append("СМЕНА СОСТАВА")
        if r["partial_month"]:
            marks.append("неполный месяц, не флагается")
        flag = ("  ← " + ", ".join(marks)) if marks else ""
        chg = "     " if pd.isna(r["chg"]) else f"{r['chg']:+5.0f}"
        ch = "    -" if pd.isna(r["churn_pct"]) else f"{r['churn_pct']:5.0f}"
        print(f"  {r['month']}  n={int(r['n_active']):4d}  плотн={int(r['n_dense']):4d}  "
              f"{chg}  +{int(r['n_new']):3d}/-{int(r['n_gone']):3d}  "
              f"churn={ch}%  {bar}{flag}")

    print("\n" + "=" * 78)
    print("ПО ГОДАМ")
    print("=" * 78)
    yr = df.copy()
    yr["year"] = yr["month"].str[:4]
    g = yr.groupby("year")["n_active"].agg(["min", "median", "max"])
    for y, r in g.iterrows():
        print(f"  {y}   min={int(r['min']):4d}  median={int(r['median']):4d}  "
              f"max={int(r['max']):4d}")

    # ── вердикт по непрерывности ─────────────────────────────────────────────
    jumps = df[df["jump_flag"] == 1]
    churns = df[df["churn_flag"] == 1]
    print("\n" + "=" * 78)
    print("ПРОВЕРКА НА СТУПЕНЧАТОСТЬ (проблема этапа 1)")
    print("=" * 78)
    print(f"  профиль этапа 1 (по неделям): 30 → 318 → 97 → 32 → 45 → 306 → 162")
    print(f"  критерий скачка : |Δ| >= {JUMP_ABS} символов И |Δ%| >= {JUMP_REL * 100:.0f}%")
    print(f"  критерий смены  : (new+gone) >= {CHURN_ABS} И churn >= {CHURN_REL * 100:.0f}%")
    if last_partial:
        print(f"  последний месяц {df['month'].iloc[-1]} неполный "
              f"(панель до {last_ts.date()}, в месяце {last_period.days_in_month} дн.) "
              f"— исключён из флагов")
    print(f"  месяцев со скачком размера : {len(jumps)} из {len(df)}")
    print(f"  месяцев со сменой состава  : {len(churns)} из {len(df)}")

    if jumps.empty and churns.empty:
        print("\n  ✓ Ни резких скачков размера, ни резкой смены состава.")
        print("    Покрытие меняется плавно — так и должно выглядеть постепенное")
        print("    расширение листинга плюс отдельные делистинги.")
        print("    Ступенчатость этапа 1 устранена.")
    else:
        print("\n  ⚠ ОБНАРУЖЕНЫ АНОМАЛИИ — зафиксировать в отчёте, не замалчивать:")
        for _, r in df[(df.jump_flag == 1) | (df.churn_flag == 1)].iterrows():
            kind = []
            if r["jump_flag"]:
                kind.append(f"размер {r['chg']:+.0f} ({r['chg_pct']:+.1f}%)")
            if r["churn_flag"]:
                kind.append(f"состав {r['churn_pct']:.0f}%")
            print(f"     {r['month']}  n={int(r['n_active']):4d}  "
                  f"+{int(r['n_new'])}/-{int(r['n_gone'])}   " + "; ".join(kind))
        print("\n  Как отличить артефакт от рынка:")
        print("    • рост в первые месяцы истории (2019-2020) — нормальный запуск")
        print("      линейки перпов, не артефакт;")
        print("    • падение с большим n_gone — вероятно реальные делистинги,")
        print("      проверить по delisted_symbols.json;")
        print("    • резкий рост с большим n_new В СЕРЕДИНЕ истории или скачок")
        print("      вверх-вниз подряд — подозрение на неполную докачку,")
        print("      проверить failures.csv и перезапустить докачку.")

    check_failures()
    report_longest_gaps(panel)

    print(f"\n→ {OUT}")


def check_failures() -> None:
    """Сверка с failures.csv: недокачанные файлы — первая версия любого скачка."""
    print("\n" + "=" * 78)
    print("СВЕРКА С failures.csv")
    print("=" * 78)
    if not FAILURES.exists():
        print("  failures.csv отсутствует — при докачке ошибок не было.")
        return
    lines = [ln for ln in FAILURES.read_text(encoding="utf-8").splitlines()
             if ln.strip() and ln.strip() != "key"]
    if not lines:
        print("  failures.csv пуст — все файлы скачаны.")
        return

    print(f"  ⚠ НЕ СКАЧАНО ФАЙЛОВ: {len(lines)}")
    print("  Часть месяцев могла не докачаться — это само по себе способно")
    print("  объяснить скачки и смену состава выше. Прежде чем трактовать")
    print("  аномалии как рыночные, перезапустите докачку:")
    print("      python download_multiyear_klines.py")
    print("  (она возьмёт только недостающее) и прогоните эту проверку заново.")

    # символ берём из имени файла (SYMBOL-1d-YYYY-MM.zip), а не по индексу
    # сегмента пути: индекс поехал бы при любом изменении префикса бакета
    by_sym: dict[str, int] = {}
    for ln in lines:
        name = ln.strip().rsplit("/", 1)[-1]
        sym = name.split("-", 1)[0]
        if sym:
            by_sym[sym] = by_sym.get(sym, 0) + 1
    if by_sym:
        top = sorted(by_sym.items(), key=lambda x: -x[1])[:TOP_GAPS]
        print(f"\n  символов затронуто: {len(by_sym)}; худшие:")
        for s, n in top:
            print(f"     {s:16s} не скачано месяцев: {n}")


def longest_internal_gap(col: pd.Series) -> tuple:
    """
    Самая длинная НЕПРЕРЫВНАЯ дыра внутри диапазона жизни символа.

    Именно непрерывная, а не суммарная: 60 разрозненных пропусков по одному дню
    и одна дыра в 60 дней подряд дают одинаковый gap_days в panel_coverage.csv,
    но означают совершенно разное. Одна длинная дыра посреди истории — это
    почти наверняка недокачанные месяцы; редкие одиночные пропуски — нормальные
    паузы в торговле.

    Возвращает (длина_дыры_в_днях, дата_начала, дата_конца).
    """
    fi, li = col.first_valid_index(), col.last_valid_index()
    if fi is None or li is None or fi == li:
        return 0, None, None
    s = col.loc[fi:li]
    isna = s.isna().to_numpy()
    if not isna.any():
        return 0, None, None
    # длины серий подряд идущих NaN
    idx = np.flatnonzero(np.diff(np.concatenate(([0], isna.view(np.int8), [0]))))
    starts, ends = idx[::2], idx[1::2]
    runs = ends - starts
    k = int(np.argmax(runs))
    return int(runs[k]), s.index[starts[k]].date(), s.index[ends[k] - 1].date()


def report_longest_gaps(panel: pd.DataFrame) -> None:
    """Топ символов по самой длинной непрерывной внутренней дыре."""
    print("\n" + "=" * 78)
    print(f"ТОП-{TOP_GAPS} СИМВОЛОВ ПО ДЛИНЕ НЕПРЕРЫВНОЙ ВНУТРЕННЕЙ ДЫРЫ")
    print("=" * 78)
    print("  Считается самая длинная дыра ПОДРЯД, а не суммарный gap_days из")
    print("  panel_coverage.csv — они различают недокачку и обычные паузы.")

    rows = []
    for sym in panel.columns:
        n, a, b = longest_internal_gap(panel[sym])
        if n > 0:
            rows.append({"symbol": sym, "max_gap_days": n,
                         "gap_from": str(a), "gap_to": str(b)})
    if not rows:
        print("\n  ✓ Внутренних дыр нет вообще: у каждого символа непрерывный ряд")
        print("    от первой до последней торговой даты.")
        return

    g = pd.DataFrame(rows).sort_values("max_gap_days", ascending=False)

    # сверка с panel_coverage.csv: суммарный gap против самой длинной дыры
    if COVERAGE.exists():
        try:
            cov = pd.read_csv(COVERAGE, sep=";")
            keep = [c for c in ("symbol", "gap_days", "trading_now")
                    if c in cov.columns]
            g = g.merge(cov[keep], on="symbol", how="left")
        except Exception as e:
            print(f"  (panel_coverage.csv не прочитан: {e})")

    delisted = set()
    if DELISTED.exists():
        try:
            import json
            delisted = set(json.loads(DELISTED.read_text(encoding="utf-8")))
        except Exception:
            pass

    print(f"\n  символов с внутренними дырами: {len(g)} из {panel.shape[1]}")
    print()
    for _, r in g.head(TOP_GAPS).iterrows():
        tot = f"  всего пропусков={int(r['gap_days'])}" if "gap_days" in r and \
              pd.notna(r.get("gap_days")) else ""
        mark = "  [делистнут]" if r["symbol"] in delisted else ""
        print(f"     {r['symbol']:16s} дыра {int(r['max_gap_days']):4d} дн.  "
              f"{r['gap_from']} → {r['gap_to']}{tot}{mark}")

    print("\n  Как читать:")
    print("    • дыра в десятки дней у ТОРГУЮЩЕГОСЯ сейчас символа — почти")
    print("      наверняка недокачанные месяцы, проверить failures.csv;")
    print("    • дыра у символа с пометкой [делистнут] — возможен реальный")
    print("      перерыв торгов или возврат после делистинга;")
    print("    • max_gap_days много меньше суммарного gap_days — это редкие")
    print("      одиночные пропуски, нормальная ситуация.")


if __name__ == "__main__":
    main()
