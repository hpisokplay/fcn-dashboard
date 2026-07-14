#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FCN 儀表板 — 美股／日股收盤報價抓取（後端批次，供 GitHub Actions 每日自動執行）

做法：伺服器端直接打 Yahoo Finance 公開端點（無 CORS 問題、免金鑰、免代理），
取得每檔標的的「現價」與「近 2 年每日最高／最低」（KI/KO 判斷用），寫出 data/prices.json。
網頁只要讀這個檔，就不必再靠不穩定的 allorigins 代理。

symbol 規則：日股用「代號.T」(6146.T)；美股用原代號，class 股把點改成連字號（BRK.B -> BRK-B）。
執行：python scripts/fetch_prices.py
"""
import csv
import json
import os
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; fcn-dashboard/1.0; personal research)"}

# 基礎清單（與網頁 stockNames 一致）；實際會再併入 data.csv 裡出現的代號
BASE_SYMBOLS = [
    "6146.T", "6501.T", "7011.T", "6857.T", "7012.T", "7013.T", "7974.T",
    "8035.T", "5803.T", "8697.T", "8002.T",
    "NVDA", "TSLA", "TSM", "AMD", "MU", "ARM", "GOOG", "AMZN", "AVGO",
    "MSFT", "META", "DELL", "ORCL", "OKLO", "PLTR", "NFLX", "BRK.B",
]


def yahoo_symbol(sym):
    """把資料裡的代號轉成 Yahoo 用的代號（日股 .T 保留；美股 class 股的 . 轉 -）"""
    s = str(sym).strip()
    return s if s.endswith(".T") else s.replace(".", "-")


def symbols_from_csv():
    """從 data.csv 讀出實際持有標的（s1_code~s4_code），確保新加的股也會被抓到"""
    found = set()
    path = os.path.join(ROOT, "data.csv")
    if not os.path.exists(path):
        return found
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                for i in range(1, 5):
                    c = (row.get(f"s{i}_code") or "").strip()
                    if c:
                        found.add(c)
    except Exception as e:  # noqa
        print(f"  讀 data.csv 失敗（略過）: {e}", file=sys.stderr)
    return found


def fetch_chart(sym, retries=3):
    """回傳 {current, timestamp[], high[], low[]}；失敗回 None"""
    ysym = yahoo_symbol(sym)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ysym}?interval=1d&range=2y"
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                j = json.loads(r.read().decode("utf-8"))
            res = j["chart"]["result"][0]
            meta = res["meta"]
            q = res["indicators"]["quote"][0]
            cur = meta.get("regularMarketPrice")
            if cur is None:
                cur = meta.get("previousClose") or meta.get("chartPreviousClose")
            return {
                "current": cur,
                "prevClose": meta.get("chartPreviousClose"),
                "currency": meta.get("currency"),
                "timestamp": res.get("timestamp") or [],
                "high": q.get("high") or [],
                "low": q.get("low") or [],
                "close": q.get("close") or [],
            }
        except Exception as e:  # noqa
            print(f"  retry {i+1}/{retries} {sym}: {e}", file=sys.stderr)
            time.sleep(2 * (i + 1))
    print(f"  FAILED {sym}", file=sys.stderr)
    return None


def main():
    symbols = sorted(set(BASE_SYMBOLS) | symbols_from_csv())
    print(f"共 {len(symbols)} 檔標的")
    out = {}
    ok = 0
    for sym in symbols:
        rec = fetch_chart(sym)
        if rec and rec.get("current") is not None:
            out[sym] = rec
            ok += 1
            print(f"  {sym}: {rec['current']} {rec.get('currency') or ''} "
                  f"({len(rec['timestamp'])} 日歷史)")
        time.sleep(0.6)  # 溫和節流，避免被 Yahoo 限流
    payload = {"updated": int(time.time()), "count": ok, "prices": out}
    with open(os.path.join(ROOT, "prices.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    print(f"完成：{ok}/{len(symbols)} 檔寫入 prices.json")
    if ok == 0:
        sys.exit(1)  # 全失敗才視為錯誤（讓 Action 顯示紅燈）


if __name__ == "__main__":
    main()
