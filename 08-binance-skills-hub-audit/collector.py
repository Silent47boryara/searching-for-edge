#!/usr/bin/env python3
"""
meme-rush radar: research data collector without AI, wallet access, or trades.

Observed public Binance Web3 endpoint:
  POST https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/pulse/rank/list/ai

The collector stores complete token payloads at each poll. Strategy rules and
performance analysis must be calculated separately from the accumulated raw
history. This is a research prototype, not a production trading system.

Stages (rankType):
  10 = new
  20 = finalizing the bonding curve
  30 = migrated

Storage: SQLite radar.db next to this script.
  raw      - complete token JSON for every poll
  events   - preliminary near-grad and graduate-in-10-min observations
  poll_log - request results

First-run limitation: the script does not know prior token state. A token that
is already above 80% on the first poll is recorded as a new near-grad event,
even when it crossed the threshold before monitoring began.
"""

import json
import sqlite3
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


URL = "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/pulse/rank/list/ai"
DB_PATH = Path(__file__).parent / "radar.db"
CHAIN_ID = "56"
PROTOCOLS = {2002: "flap", 2001: "fourmeme"}
STAGES = {10: "new", 20: "finalizing", 30: "migrated"}
NEAR_GRAD_THRESHOLD = 80.0
GRADUATE_WINDOW_MIN = 10
TIMEOUT_S = 15

HEADERS = {
    "Content-Type": "application/json",
    "Accept-Encoding": "identity",
    "User-Agent": "karaptic-radar/0.2 (research collector)",
}


def fetch(rank_type, protocol, limit=200):
    body = {
        "chainId": CHAIN_ID,
        "rankType": rank_type,
        "protocol": [protocol],
        "limit": limit,
    }
    request = urllib.request.Request(
        URL,
        data=json.dumps(body).encode(),
        headers=HEADERS,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
        payload = json.loads(response.read())
    return payload.get("data") or []


def init_db(connection):
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS raw(
            ts INTEGER, stage INTEGER, protocol TEXT,
            contract TEXT, symbol TEXT, payload TEXT
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_raw_contract ON raw(contract)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_raw_ts ON raw(ts)")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS events(
            ts INTEGER, contract TEXT, protocol TEXT, symbol TEXT,
            event_type TEXT, detail TEXT,
            UNIQUE(contract, event_type)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS poll_log(
            ts INTEGER, protocol TEXT, stage INTEGER,
            tokens_fetched INTEGER, ok INTEGER, note TEXT
        )
        """
    )
    connection.commit()


def record_event(connection, ts, contract, protocol, symbol, event_type, detail):
    try:
        connection.execute(
            "INSERT INTO events(ts,contract,protocol,symbol,event_type,detail) "
            "VALUES (?,?,?,?,?,?)",
            (ts, contract, protocol, symbol, event_type, detail),
        )
        print(
            f"[EVENT] {event_type:28s} {symbol:14s} "
            f"{contract[:12]}...  {detail}"
        )
    except sqlite3.IntegrityError:
        pass


def poll_once(connection):
    ts = int(time.time())
    for protocol_code, protocol_name in PROTOCOLS.items():
        for rank_type, stage_name in STAGES.items():
            try:
                tokens = fetch(rank_type=rank_type, protocol=protocol_code)
                ok = 1
            except (
                urllib.error.URLError,
                TimeoutError,
                json.JSONDecodeError,
                OSError,
            ) as error:
                print(f"[WARN] {protocol_name} stage={stage_name}: {error}")
                tokens = []
                ok = 0

            connection.execute(
                "INSERT INTO poll_log VALUES (?,?,?,?,?,?)",
                (ts, protocol_name, rank_type, len(tokens), ok, ""),
            )

            for token in tokens:
                connection.execute(
                    "INSERT INTO raw VALUES (?,?,?,?,?,?)",
                    (
                        ts,
                        rank_type,
                        protocol_name,
                        token.get("contractAddress"),
                        token.get("symbol"),
                        json.dumps(token, ensure_ascii=False),
                    ),
                )

                if rank_type == 20:
                    progress = float(token.get("progress") or 0)
                    if progress >= NEAR_GRAD_THRESHOLD:
                        record_event(
                            connection,
                            ts,
                            token["contractAddress"],
                            protocol_name,
                            token.get("symbol"),
                            f"{protocol_name}_near_grad",
                            f"progress={progress:.1f}%",
                        )

                if rank_type == 30:
                    create_time = token.get("createTime")
                    migrate_time = token.get("migrateTime")
                    if (
                        create_time
                        and migrate_time
                        and token.get("migrateStatus") == 1
                    ):
                        minutes = (migrate_time - create_time) / 60000
                        if minutes <= GRADUATE_WINDOW_MIN:
                            record_event(
                                connection,
                                ts,
                                token["contractAddress"],
                                protocol_name,
                                token.get("symbol"),
                                f"{protocol_name}_graduate_in_"
                                f"{GRADUATE_WINDOW_MIN}min",
                                f"{minutes:.2f} minutes from creation to migration",
                            )

    connection.commit()


def summary(connection):
    raw_rows = connection.execute("SELECT COUNT(*) FROM raw").fetchone()[0]
    contracts = connection.execute(
        "SELECT COUNT(DISTINCT contract) FROM raw"
    ).fetchone()[0]
    events = connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    first = connection.execute("SELECT MIN(ts) FROM raw").fetchone()[0]
    last = connection.execute("SELECT MAX(ts) FROM raw").fetchone()[0]

    span = ""
    if first and last:
        first_time = datetime.fromtimestamp(first, tz=timezone.utc)
        last_time = datetime.fromtimestamp(last, tz=timezone.utc)
        span = f", history {first_time:%H:%M}-{last_time:%H:%M} UTC"

    print(
        f"\nDatabase: {raw_rows} raw rows, {contracts} unique contracts, "
        f"{events} events{span}"
    )


if __name__ == "__main__":
    database = sqlite3.connect(DB_PATH)
    init_db(database)
    poll_once(database)
    summary(database)
    database.close()
