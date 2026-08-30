#!/usr/bin/env python3
"""
Lab 06, ЭТАП 2 — сборка скачанного в единую панель дата × символ.

ЗАПУСКАТЬ ОТДЕЛЬНО, ПОСЛЕ того как download_multiyear_klines.py отработал.
Сеть не используется — только чтение локальных zip.

На выходе:
  panel_close.csv        — дата × символ, цена закрытия дня
  panel_quote_volume.csv — дата × символ, оборот в котируемой валюте
                           (нужен на следующем шаге для фильтра ликвидности:
                            momentum на неликвиде нереализуем)
  panel_coverage.csv     — по символу: первая/последняя дата, число дней,
                           пропуски внутри диапазона, торгуется ли сейчас

Пропуски НЕ заполняются. Отсутствие дня = монета в тот день не торговалась.
Никакого forward-fill: он превратил бы делистнутую монету в «замороженную,
но живую» и исказил бы именно ту шорт-ногу, ради которой затевалась докачка.
"""

import io
import json
import zipfile
from pathlib import Path

import pandas as pd

HERE    = Path(__file__).resolve().parent
RAW_DIR = HERE / "raw"

KCOLS = ["open_time", "open", "high", "low", "close", "volume", "close_time",
         "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume",
         "ignore"]


def read_zip(p: Path) -> pd.DataFrame:
    """Читает единственный CSV из zip. Заголовок определяется по первой ячейке."""
    try:
        with zipfile.ZipFile(p) as z:
            raw = z.read(z.namelist()[0])
    except (zipfile.BadZipFile, IndexError, OSError):
        return pd.DataFrame()
    if not raw:
        return pd.DataFrame()
    first = raw.split(b"\n", 1)[0].split(b",")[0].strip()
    has_hdr = not first.replace(b".", b"", 1).isdigit()
    try:
        d = (pd.read_csv(io.BytesIO(raw)) if has_hdr
             else pd.read_csv(io.BytesIO(raw), header=None, names=KCOLS))
    except Exception:
        return pd.DataFrame()
    d.columns = [str(c).strip().lower() for c in d.columns]
    return d


# Поля, попадающие в панели. `open` добавлен для Lab 06 / step3: там вход по
# open понедельника и выход по open следующего понедельника, и смешивать open
# на входе с close на выходе нельзя — это внесло бы асимметричное искажение.
VALUE_COLS = ("open", "close", "quote_volume")


def load_symbol(sym_dir: Path) -> pd.DataFrame:
    """Все месячные архивы символа → DataFrame(date, open, close, quote_volume)."""
    parts = []
    for f in sorted(sym_dir.rglob("*.zip")):
        d = read_zip(f)
        if d.empty or "open_time" not in d.columns:
            continue
        keep = [c for c in ("open_time",) + VALUE_COLS if c in d.columns]
        parts.append(d[keep])
    if not parts:
        return pd.DataFrame()

    k = pd.concat(parts, ignore_index=True)
    k["open_time"] = pd.to_numeric(k["open_time"], errors="coerce")
    k = k.dropna(subset=["open_time"])
    if k.empty:
        return pd.DataFrame()
    # Binance перешёл на микросекунды в свежих файлах — определяем по величине
    unit = "us" if k["open_time"].max() > 1e15 else "ms"
    k["date"] = pd.to_datetime(k["open_time"], unit=unit, utc=True).dt.tz_localize(None)
    for c in VALUE_COLS:
        if c in k.columns:
            k[c] = pd.to_numeric(k[c], errors="coerce")
    # Дедуп и сортировка — как были. dropna по close оставлен единственным
    # критерием валидности строки, чтобы panel_open строился РОВНО из того же
    # набора дат и символов, что и panel_close (иначе панели разъедутся).
    k = (k.dropna(subset=["close"])
           .drop_duplicates("date")
           .set_index("date")
           .sort_index())
    return k[[c for c in VALUE_COLS if c in k.columns]]


def main() -> None:
    if not RAW_DIR.exists():
        raise SystemExit(f"[ERR] нет {RAW_DIR} — сначала download_multiyear_klines.py")

    dirs = sorted(d for d in RAW_DIR.iterdir() if d.is_dir())
    print(f"[PANEL] символов на диске: {len(dirs)}")

    opens, closes, vols, cov = {}, {}, {}, []
    for i, d in enumerate(dirs, 1):
        df = load_symbol(d)
        if df.empty:
            continue
        closes[d.name] = df["close"]
        if "open" in df.columns:
            opens[d.name] = df["open"]
        if "quote_volume" in df.columns:
            vols[d.name] = df["quote_volume"]
        span = (df.index.max() - df.index.min()).days + 1
        cov.append({"symbol": d.name,
                    "first_date": df.index.min().date().isoformat(),
                    "last_date": df.index.max().date().isoformat(),
                    "n_days": len(df),
                    "span_days": span,
                    "gap_days": span - len(df)})
        if i % 100 == 0:
            print(f"  ...{i}/{len(dirs)}  собрано={len(closes)}", flush=True)

    if not closes:
        raise SystemExit("[ERR] не собрано ни одного символа")

    panel = pd.DataFrame(closes).sort_index()
    panel.to_csv(HERE / "panel_close.csv", sep=";")

    # panel_open строится на ТОЙ ЖЕ сетке дат и символов, что panel_close:
    # reindex по panel гарантирует совпадение формы даже если у какого-то
    # символа поле open отсутствовало в части архивов. Пропуски остаются
    # пропусками — никакого forward fill.
    if opens:
        panel_open = pd.DataFrame(opens).reindex(
            index=panel.index, columns=panel.columns)
        panel_open.to_csv(HERE / "panel_open.csv", sep=";")
    if vols:
        panel_vol = pd.DataFrame(vols).reindex(
            index=panel.index, columns=panel.columns)
        panel_vol.to_csv(HERE / "panel_quote_volume.csv", sep=";")

    covdf = pd.DataFrame(cov).sort_values("symbol")
    dl = HERE / "delisted_symbols.json"
    if dl.exists():
        gone = set(json.loads(dl.read_text(encoding="utf-8")))
        covdf["trading_now"] = (~covdf["symbol"].isin(gone)).astype(int)
    covdf.to_csv(HERE / "panel_coverage.csv", sep=";", index=False)

    print(f"\n[PANEL] панель: {panel.shape[0]} дней × {panel.shape[1]} символов")
    print(f"[PANEL] период : {panel.index.min().date()} → {panel.index.max().date()}")
    print(f"[PANEL] символов с пропусками внутри диапазона: "
          f"{(covdf.gap_days > 0).sum()}")
    if "trading_now" in covdf.columns:
        print(f"[PANEL] делистнутых (нет в exchangeInfo): "
              f"{int((covdf.trading_now == 0).sum())}")
    if opens:
        n_close = int(panel.notna().sum().sum())
        n_open = int(panel_open.notna().sum().sum())
        print(f"[PANEL] непустых ячеек: close={n_close}  open={n_open}"
              f"  расхождение={n_close - n_open}")
        if n_close != n_open:
            print("        (open отсутствует в части архивов — ячейки оставлены "
                  "пустыми, forward fill не применялся)")

    print(f"\n→ {HERE / 'panel_close.csv'}")
    if opens:
        print(f"→ {HERE / 'panel_open.csv'}")
    if vols:
        print(f"→ {HERE / 'panel_quote_volume.csv'}")
    print(f"→ {HERE / 'panel_coverage.csv'}")


if __name__ == "__main__":
    main()
