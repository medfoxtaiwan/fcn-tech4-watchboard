#!/usr/bin/env python3
"""FCN watchboard — 每日抓取 NVDA/TSM/GOOG 收盤價並產出 data.json

結構型商品條件（2026-06-17 進場，2026-10-17 到期，4 個月）：
  提前出場價 (Knock-Out, KO) = 進場價 100%，滿一個月（2026-07-17 起）皆曾漲過 → 提前出場
  下限價 (Knock-In, KI)      = 進場價 70%，期間任一檔跌破 → 下檔保護失效
  執行價 (Strike)            = 進場價 75.61%，到期最差標的低於執行價 → 以執行價接該檔
跌破判定以【收盤價】為準（使用者指定）；盤中低點跌破另記為 intraday 參考。
每次執行從進場日重抓全程歷史、全量重算，無需保存狀態。
"""
import json
import datetime
import time
import urllib.request

TICKERS = {"NVDA": 204.65, "TSM": 432.15, "GOOG": 362.10}
BARRIER_RATIO = 0.70
STRIKE_RATIO = 0.7561
ENTRY_DATE = datetime.date(2026, 6, 17)
KO_START = datetime.date(2026, 7, 17)   # 滿一個月
MATURITY = datetime.date(2026, 10, 17)
BREAKEVEN = {"NVDA": 151, "TSM": 319, "GOOG": 267}  # 含息損益兩平價(估值)

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
HOSTS = ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]


def fetch_chart(ticker: str) -> dict:
    p1 = int(datetime.datetime(2026, 6, 16, tzinfo=datetime.timezone.utc).timestamp())
    p2 = int(time.time())
    last_err = None
    for attempt in range(4):
        host = HOSTS[attempt % len(HOSTS)]
        url = (f"https://{host}/v8/finance/chart/{ticker}"
               f"?period1={p1}&period2={p2}&interval=1d")
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
            result = data["chart"]["result"][0]
            if result["indicators"]["quote"][0]["close"]:
                return result
        except Exception as e:  # noqa: BLE001 — 重試涵蓋網路/解析錯誤
            last_err = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"{ticker} fetch failed: {last_err}")


def build_series(result: dict) -> list[dict]:
    ts = result["timestamp"]
    q = result["indicators"]["quote"][0]
    tz = datetime.timezone(datetime.timedelta(hours=result["meta"].get("gmtoffset", -14400) // 3600))
    rows = []
    for i, t in enumerate(ts):
        if q["close"][i] is None:
            continue
        d = datetime.datetime.fromtimestamp(t, tz).date()
        if d < ENTRY_DATE or d > MATURITY:
            continue
        rows.append({
            "date": str(d),
            "close": round(q["close"][i], 2),
            "low": round(q["low"][i], 2) if q["low"][i] else None,
            "high": round(q["high"][i], 2) if q["high"][i] else None,
        })
    # 同日重複(盤中快照)取最後一筆
    dedup = {}
    for r in rows:
        dedup[r["date"]] = r
    return sorted(dedup.values(), key=lambda r: r["date"])


def analyze(ticker: str, entry: float, rows: list[dict]) -> dict:
    barrier = round(entry * BARRIER_RATIO, 4)
    strike = round(entry * STRIKE_RATIO, 4)
    latest = rows[-1]
    min_row = min(rows, key=lambda r: r["close"])
    close_breaches = [
        {"date": r["date"], "close": r["close"],
         "pct_below": round((barrier - r["close"]) / barrier * 100, 2)}
        for r in rows if r["close"] < barrier
    ]
    intraday_breaches = [
        {"date": r["date"], "low": r["low"], "close": r["close"]}
        for r in rows if r["low"] is not None and r["low"] < barrier and r["close"] >= barrier
    ]
    ko_any = next((r["date"] for r in rows if r["close"] > entry), None)
    ko_after_1m = next(
        (r["date"] for r in rows
         if datetime.date.fromisoformat(r["date"]) >= KO_START and r["close"] > entry),
        None,
    )
    return {
        "entry": entry,
        "barrier": barrier,
        "strike": strike,
        "breakeven": BREAKEVEN[ticker],
        "latest_date": latest["date"],
        "latest_close": latest["close"],
        "vs_entry_pct": round((latest["close"] - entry) / entry * 100, 2),
        "buffer_to_barrier_pct": round((latest["close"] - barrier) / latest["close"] * 100, 2),
        "drawdown_to_barrier_pct": round((barrier - latest["close"]) / latest["close"] * 100, 2),
        "min_close": min_row,
        "close_breaches": close_breaches,
        "intraday_breaches": intraday_breaches,
        "ever_breached": len(close_breaches) > 0,
        "ko_first_close_above_entry": ko_any,
        "ko_first_close_above_entry_after_1m": ko_after_1m,
        "series": [{"date": r["date"], "close": r["close"]} for r in rows],
    }


def main() -> None:
    out = {
        "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "entry_date": str(ENTRY_DATE),
        "maturity_date": str(MATURITY),
        "ko_start_date": str(KO_START),
        "barrier_ratio": BARRIER_RATIO,
        "strike_ratio": STRIKE_RATIO,
        "stocks": {},
    }
    for ticker, entry in TICKERS.items():
        result = fetch_chart(ticker)
        rows = build_series(result)
        out["stocks"][ticker] = analyze(ticker, entry, rows)
        print(f"{ticker}: {len(rows)} 交易日, 最新 {rows[-1]['date']} 收盤 {rows[-1]['close']}, "
              f"跌破 {len(out['stocks'][ticker]['close_breaches'])} 次")
        time.sleep(1)

    latest_date = max(s["latest_date"] for s in out["stocks"].values())
    out["days_to_maturity"] = (MATURITY - datetime.date.fromisoformat(latest_date)).days
    ko_dates = [s["ko_first_close_above_entry_after_1m"] for s in out["stocks"].values()]
    out["ko_condition_met"] = all(ko_dates)
    out["ko_met_date"] = max(ko_dates) if out["ko_condition_met"] else None
    out["total_close_breaches"] = sum(len(s["close_breaches"]) for s in out["stocks"].values())

    with open(__file__.rsplit("/", 1)[0] + "/data.json", "w") as f:
        json.dump(out, f, ensure_ascii=False)
    print(f"data.json 更新完成 (KO 條件達成: {out['ko_condition_met']}, "
          f"總跌破次數: {out['total_close_breaches']}, 距到期 {out['days_to_maturity']} 天)")


if __name__ == "__main__":
    main()
