#!/usr/bin/env python3
"""
Lab 06, ЭТАП 2 — докачка полной многолетней истории 1d-klines
по ВСЕЙ вселенной USDT-M бессрочных фьючерсов.

ЗАЧЕМ ИМЕННО S3-ЛИСТИНГ, А НЕ /fapi/v1/exchangeInfo
────────────────────────────────────────────────────────────────────────────
exchangeInfo возвращает только то, что торгуется СЕЙЧАС. Все монеты,
делистнутые в прошлом, из него исчезают — и бэктест задним числом
избавляется от «умирающих» слабых активов. Для шорт-ноги momentum-стратегии
это систематическая ошибка в свою пользу (survivorship bias).

S3-бакет `data.binance.vision` — архив, а не live-статус: делистнутые
символы в нём остаются. Проверено на момент написания скрипта:
  символов USDT-перпов в архиве      : 832
  есть в архиве, нет в exchangeInfo  : 31
  (AERGOUSDT, AKROUSDT, ANCUSDT, ANTUSDT, BTCSTUSDT, BZRXUSDT, BTTUSDT, ...)
Эта 31 монета — ровно то, что было бы потеряно при использовании exchangeInfo.

ЧТО КАЧАЕТ
────────────────────────────────────────────────────────────────────────────
Только 1d-klines (месячные архивы). Ни OI, ни funding — они нужны на этапе 3
(издержки), а не при первичном тесте на спред.

Полная доступная история: диапазон месяцев НЕ угадывается и не задаётся
руками — для каждого символа берётся точный список файлов из S3-листинга
его собственной папки. Это исключает как обрезку истории, так и шквал 404.

ПРОДОЛЖЕНИЕ ПОСЛЕ ПРЕРЫВАНИЯ
────────────────────────────────────────────────────────────────────────────
Двухуровневый checkpoint:
  1. manifest.json — закэшированные списки файлов по символам, чтобы при
     перезапуске не выполнять 832 листинг-запроса заново.
  2. Сами файлы на диске — уже скачанный и валидный zip пропускается.
Состояние сбрасывается на диск периодически и по Ctrl-C. Прерывать безопасно
в любой момент: повторный запуск продолжит с места остановки.

ЗАПУСК: см. README_step2.md
"""

import argparse
import io
import json
import logging
import signal
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

import requests

# ── константы ────────────────────────────────────────────────────────────────
S3_ENDPOINT = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
CDN_BASE    = "https://data.binance.vision"
S3_NS       = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
KLINES_PREFIX = "data/futures/um/monthly/klines/"

HERE      = Path(__file__).resolve().parent
RAW_DIR   = HERE / "raw"
MANIFEST  = HERE / "manifest.json"
FAILURES  = HERE / "failures.csv"
LOG_FILE  = HERE / "download.log"

RETRY_MAX      = 5
RETRY_BASE_SEC = 1.0
TIMEOUT_SEC    = 60
STATE_FLUSH_EVERY = 25          # как часто сбрасывать manifest на диск

_stop = False
_lock = Lock()


def _sigint(signum, frame):
    global _stop
    if _stop:
        log.warning("повторный Ctrl-C — выходим немедленно")
        sys.exit(130)
    _stop = True
    log.warning("получен Ctrl-C — доканчиваем текущие загрузки и сохраняем "
                "состояние (повторный Ctrl-C прервёт немедленно)")


# ── логирование ──────────────────────────────────────────────────────────────
log = logging.getLogger("lab06_step2")


def setup_logging(verbose: bool) -> None:
    log.setLevel(logging.DEBUG if verbose else logging.INFO)
    fmt = logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s",
                            datefmt="%H:%M:%S")
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    log.addHandler(sh)
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-7s  %(message)s"))
    log.addHandler(fh)


# ── сеть ─────────────────────────────────────────────────────────────────────
def http_get(url: str, params: dict | None = None,
             session: requests.Session | None = None) -> requests.Response | None:
    """
    GET с повторами. 429 и 5xx — ретраим с экспоненциальной паузой,
    уважая Retry-After. 404 возвращаем как есть (нормальная ситуация).
    """
    get = (session or requests).get
    for attempt in range(RETRY_MAX):
        if _stop:
            return None
        try:
            r = get(url, params=params, timeout=TIMEOUT_SEC)
            if r.status_code == 404:
                return r
            if r.status_code == 429 or 500 <= r.status_code < 600:
                wait = float(r.headers.get("Retry-After",
                                           RETRY_BASE_SEC * (2 ** attempt)))
                log.debug(f"HTTP {r.status_code} на {url} — пауза {wait:.1f}с "
                          f"(попытка {attempt + 1}/{RETRY_MAX})")
                time.sleep(min(wait, 60))
                continue
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            wait = RETRY_BASE_SEC * (2 ** attempt)
            log.debug(f"сетевая ошибка {type(e).__name__} на {url} — "
                      f"пауза {wait:.1f}с (попытка {attempt + 1}/{RETRY_MAX})")
            time.sleep(wait)
    log.error(f"НЕ УДАЛОСЬ после {RETRY_MAX} попыток: {url}")
    return None


def s3_list(prefix: str, delimiter: str = "/") -> tuple[list[str], list[str]]:
    """
    Постраничный листинг бакета (ListObjects v1, marker-пагинация).
    Возвращает (common_prefixes, keys). Пагинация обязательна: на момент
    написания в klines-префиксе 986 записей при лимите страницы 1000 —
    запас почти исчерпан и будет превышен по мере добавления символов.
    """
    prefixes, keys, marker = [], [], None
    while True:
        if _stop:
            break
        p = {"prefix": prefix, "delimiter": delimiter}
        if marker:
            p["marker"] = marker
        r = http_get(S3_ENDPOINT, params=p)
        if r is None or r.status_code != 200:
            break
        root = ET.fromstring(r.content)
        page_pref = [e.find("s3:Prefix", S3_NS).text
                     for e in root.findall("s3:CommonPrefixes", S3_NS)]
        page_keys = [e.find("s3:Key", S3_NS).text
                     for e in root.findall("s3:Contents", S3_NS)]
        prefixes += page_pref
        keys += page_keys
        trunc = (root.findtext("s3:IsTruncated", default="false", namespaces=S3_NS)
                 == "true")
        if not trunc:
            break
        nm = root.findtext("s3:NextMarker", namespaces=S3_NS)
        marker = nm or (page_pref or page_keys)[-1]
    return prefixes, keys


# ── отбор символов ───────────────────────────────────────────────────────────
def is_perpetual(sym: str) -> bool:
    """
    Бессрочный контракт. Отсекаем поставочные/квартальные — у них в имени
    суффикс с датой экспирации: BTCUSDT_250926, BTCBUSD_210129.
    """
    if "_" not in sym:
        return True
    tail = sym.rsplit("_", 1)[-1]
    return not (tail.isdigit() and len(tail) in (6, 8))


def discover_symbols(quote: str) -> list[str]:
    log.info("листинг символов из S3-архива (это не exchangeInfo — "
             "включает делистнутые)...")
    prefixes, _ = s3_list(KLINES_PREFIX)
    all_syms = [p[len(KLINES_PREFIX):].strip("/") for p in prefixes]

    perp = [s for s in all_syms if is_perpetual(s)]
    expiry = len(all_syms) - len(perp)

    # хвост SETTLED — артефакты переселения контрактов, не торгуемые инструменты
    perp = [s for s in perp if not s.endswith("SETTLED")]

    if quote.upper() == "ALL":
        sel = perp
    else:
        sel = [s for s in perp if s.endswith(quote.upper())]

    log.info(f"  всего префиксов в архиве      : {len(all_syms)}")
    log.info(f"  отсеяно поставочных/квартальных: {expiry}")
    log.info(f"  бессрочных                    : {len(perp)}")
    log.info(f"  отобрано с котировкой {quote.upper():5s}   : {len(sel)}")
    return sorted(sel)


def audit_survivorship(symbols: list[str]) -> None:
    """
    Диагностика: сколько символов архива отсутствует в exchangeInfo.
    Чисто информационная — на отбор не влияет, нужна для RESULT.md.
    """
    try:
        r = requests.get("https://fapi.binance.com/fapi/v1/exchangeInfo",
                         timeout=30)
        r.raise_for_status()
        live = {s["symbol"] for s in r.json()["symbols"]}
    except Exception as e:
        log.warning(f"не удалось получить exchangeInfo для диагностики: {e}")
        return
    gone = sorted(set(symbols) - live)
    log.info(f"  из них НЕ торгуются сейчас     : {len(gone)}  "
             f"← спасено от survivorship bias")
    if gone:
        log.info(f"    примеры: {', '.join(gone[:10])}")
    (HERE / "delisted_symbols.json").write_text(
        json.dumps(gone, indent=1), encoding="utf-8")


# ── manifest (checkpoint уровня 1) ───────────────────────────────────────────
def load_manifest() -> dict:
    if MANIFEST.exists():
        try:
            return json.loads(MANIFEST.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            log.warning("manifest.json повреждён — начинаем листинг заново")
    return {}


def save_manifest(m: dict) -> None:
    tmp = MANIFEST.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(m, indent=1), encoding="utf-8")
    tmp.replace(MANIFEST)          # атомарная замена: не портим файл при Ctrl-C


def list_symbol_files(sym: str, interval: str,
                      session: requests.Session) -> list[str]:
    """
    Точный список месячных архивов конкретного символа.
    Берём из листинга, а не угадываем диапазон дат: иначе либо обрежем
    историю, либо получим тысячи 404.
    """
    prefix = f"{KLINES_PREFIX}{sym}/{interval}/"
    _, keys = s3_list(prefix, delimiter="")
    return sorted(k for k in keys if k.endswith(".zip"))


def build_manifest(symbols: list[str], interval: str, workers: int) -> dict:
    man = load_manifest()
    todo = [s for s in symbols if s not in man]
    if not todo:
        log.info(f"manifest готов из кэша: {len(man)} символов")
        return man

    log.info(f"листинг файлов по символам: {len(todo)} осталось "
             f"(из кэша уже {len(man)})")
    done = 0
    with requests.Session() as ses, ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(list_symbol_files, s, interval, ses): s for s in todo}
        for f in as_completed(futs):
            if _stop:
                break
            sym = futs[f]
            try:
                man[sym] = f.result()
            except Exception as e:
                log.error(f"листинг {sym} упал: {e}")
                continue
            done += 1
            if done % STATE_FLUSH_EVERY == 0:
                with _lock:
                    save_manifest(man)
                log.info(f"  листинг {done}/{len(todo)} символов")
    save_manifest(man)
    log.info(f"manifest сохранён: {len(man)} символов, "
             f"{sum(len(v) for v in man.values())} файлов")
    return man


# ── загрузка (checkpoint уровня 2 — файлы на диске) ──────────────────────────
def is_valid_zip(p: Path) -> bool:
    if not p.exists() or p.stat().st_size == 0:
        return False
    try:
        with zipfile.ZipFile(p) as z:
            return z.testzip() is None
    except zipfile.BadZipFile:
        return False


def fetch_one(key: str, session: requests.Session) -> str:
    """'skip' | 'ok' | 'missing' | 'error'"""
    dest = RAW_DIR / Path(key).relative_to(KLINES_PREFIX)
    if is_valid_zip(dest):
        return "skip"
    if _stop:
        return "error"

    r = http_get(f"{CDN_BASE}/{key}", session=session)
    if r is None:
        return "error"
    if r.status_code == 404:
        return "missing"
    try:
        zipfile.ZipFile(io.BytesIO(r.content)).testzip()   # валидируем ДО записи
    except zipfile.BadZipFile:
        log.error(f"битый архив (не записан): {key}")
        return "error"
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".zip.part")
    tmp.write_bytes(r.content)
    tmp.replace(dest)              # атомарно: на диске либо целый файл, либо ничего
    return "ok"


def download_all(man: dict, workers: int) -> dict:
    keys = [k for v in man.values() for k in v]
    total = len(keys)
    log.info(f"к загрузке: {total} файлов, потоков: {workers}")

    stats = {"ok": 0, "skip": 0, "missing": 0, "error": 0}
    failed: list[str] = []
    t0 = time.time()

    with requests.Session() as ses, ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fetch_one, k, ses): k for k in keys}
        for i, f in enumerate(as_completed(futs), 1):
            key = futs[f]
            try:
                res = f.result()
            except Exception as e:
                log.error(f"{key}: {e}")
                res = "error"
            stats[res] += 1
            if res == "error":
                failed.append(key)
            if i % 500 == 0 or i == total:
                el = time.time() - t0
                rate = i / el if el else 0
                eta = (total - i) / rate / 60 if rate else 0
                log.info(f"  {i}/{total}  {rate:.0f} ф/с  ETA {eta:.0f} мин  "
                         f"ok={stats['ok']} skip={stats['skip']} "
                         f"miss={stats['missing']} err={stats['error']}")
            if _stop and i % 50 == 0:
                log.warning("останов по Ctrl-C — прогресс сохранён на диске")
                break

    if failed:
        FAILURES.write_text("key\n" + "\n".join(failed), encoding="utf-8")
        log.warning(f"неудачных файлов: {len(failed)} → {FAILURES}")
        log.warning("перезапустите скрипт — он продолжит только с недостающих")
    return stats


# ── CLI ──────────────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(
        description="Lab 06 этап 2: докачка многолетних 1d-klines "
                    "по всей вселенной USDT-M перпов (включая делистнутые)")
    ap.add_argument("--interval", default="1d",
                    help="интервал свечей (по умолчанию 1d)")
    ap.add_argument("--quote", default="USDT",
                    help="котируемая валюта: USDT (по умолчанию), USDC, ALL")
    ap.add_argument("--workers", type=int, default=12,
                    help="параллельных загрузок (по умолчанию 12)")
    ap.add_argument("--dry-run", action="store_true",
                    help="только листинг и оценка объёма, без загрузки")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    setup_logging(args.verbose)
    signal.signal(signal.SIGINT, _sigint)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    log.info("=" * 70)
    log.info("Lab 06 / этап 2 — многолетние 1d-klines, вся вселенная перпов")
    log.info("=" * 70)

    symbols = discover_symbols(args.quote)
    if not symbols:
        sys.exit("[ERR] не отобрано ни одного символа")
    audit_survivorship(symbols)

    man = build_manifest(symbols, args.interval, args.workers)
    if _stop:
        log.warning("прервано на этапе листинга — manifest сохранён, "
                    "перезапуск продолжит с места остановки")
        return

    total_files = sum(len(v) for v in man.values())
    have = sum(1 for v in man.values() for k in v
               if is_valid_zip(RAW_DIR / Path(k).relative_to(KLINES_PREFIX)))
    log.info(f"файлов всего: {total_files}, уже на диске: {have}, "
             f"осталось: {total_files - have}")

    if args.dry_run:
        log.info(f"[dry-run] оценка объёма: ~{total_files * 1.5 / 1024:.0f} МБ "
                 f"(месячный 1d-архив ≈ 1-2 КБ)")
        log.info("[dry-run] загрузка не выполнялась")
        return

    stats = download_all(man, args.workers)

    log.info("=" * 70)
    log.info(f"ИТОГ: {stats}")
    log.info(f"  ok      — скачано в этом запуске")
    log.info(f"  skip    — уже было на диске (checkpoint сработал)")
    log.info(f"  missing — 404, файла нет в архиве")
    log.info(f"  error   — не удалось; перезапустите скрипт")
    log.info(f"сырые файлы: {RAW_DIR}")
    log.info("следующий шаг (отдельно): python build_panel.py")


if __name__ == "__main__":
    main()
