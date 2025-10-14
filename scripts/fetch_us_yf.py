"""Fetch US index price & dividend data via Yahoo Finance."""

from __future__ import annotations

import datetime as dt
import json
from typing import Iterable

import numpy as np
import pandas as pd
import yfinance as yf

from .common import ensure_data_dir, load_indices


RAW_DIR = ensure_data_dir("raw", "us_index")
PRICE_FILENAME = "{code}_price.csv"
DIVIDEND_FILENAME = "{code}_dividend.csv"


def _candidate_symbols(cfg: dict[str, object]) -> list[str]:
    candidates: list[str] = []
    primary = cfg.get("price_symbol")
    if isinstance(primary, str) and primary:
        candidates.append(primary)
    return list(dict.fromkeys(candidates))


def _candidate_proxies(cfg: dict[str, object]) -> list[str]:
    proxies = []
    raw = cfg.get("etf_proxies") or []
    if isinstance(raw, Iterable):
        for ticker in raw:
            if isinstance(ticker, str):
                proxies.append(ticker)
    return list(dict.fromkeys(proxies))


def fetch_price(symbols: list[str], start: dt.date) -> pd.DataFrame:
    last_error: Exception | None = None
    for symbol in symbols:
        try:
            df = yf.download(symbol, start=start.isoformat(), progress=False, auto_adjust=False)
            if df.empty:
                continue
            prices = df.reset_index()[["Date", "Close"]]
            prices.columns = ["date", "close"]
            prices["date"] = pd.to_datetime(prices["date"])
            prices = prices.dropna(subset=["date", "close"]).sort_values("date")
            if not prices.empty:
                return prices
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue
    if last_error:
        raise last_error
    raise RuntimeError("未能获取指数行情数据")


def fetch_dividend_yield(proxies: list[str], start: dt.date) -> pd.DataFrame:
    last_error: Exception | None = None
    for proxy in proxies:
        try:
            ticker = yf.Ticker(proxy)
            history = ticker.history(start=start.isoformat(), auto_adjust=False)
            if history.empty:
                continue
            history.index = pd.to_datetime(history.index)
            dividends = ticker.dividends
            dividends.index = pd.to_datetime(dividends.index)
            frame = history[["Close"]].rename(columns={"Close": "close"})
            frame["dividend"] = dividends.reindex(frame.index, fill_value=0.0)
            frame["dividend_ttm"] = frame["dividend"].rolling(window="365D").sum()
            frame["dividend_yield"] = frame["dividend_ttm"] / frame["close"]
            frame.replace([np.inf, -np.inf], np.nan, inplace=True)
            frame = frame.dropna(subset=["dividend_yield"])
            if frame.empty:
                continue
            result = frame.reset_index()[["Date", "dividend_yield"]]
            result.columns = ["date", "dividend_yield"]
            result["source"] = proxy
            return result.sort_values("date")
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue
    if last_error:
        raise last_error
    raise RuntimeError("未能计算股息率")


def main() -> None:
    indices = [entry for entry in load_indices() if entry.get("class") == "US_INDEX"]
    start_date = dt.date.today() - dt.timedelta(days=365 * 15)
    summary: list[dict[str, object]] = []

    for cfg in indices:
        code = cfg["code"]
        try:
            price_df = fetch_price(_candidate_symbols(cfg), start_date)
            price_path = RAW_DIR / PRICE_FILENAME.format(code=code)
            price_df.to_csv(price_path, index=False)

            dividend_df = fetch_dividend_yield(_candidate_proxies(cfg), start_date)
            dividend_path = RAW_DIR / DIVIDEND_FILENAME.format(code=code)
            dividend_df.to_csv(dividend_path, index=False)

            summary.append(
                {
                    "code": code,
                    "price_rows": int(len(price_df)),
                    "dividend_rows": int(len(dividend_df)),
                    "dividend_source": dividend_df["source"].iloc[-1],
                }
            )
            print(f"[US_INDEX] {code} -> 行情 {len(price_df)} 行, 股息率 {len(dividend_df)} 行")
        except Exception as exc:  # noqa: BLE001
            error_path = RAW_DIR / f"{code}_error.log"
            error_path.write_text(str(exc), encoding="utf-8")
            print(f"[US_INDEX] {code} 抓取失败: {exc}")

    (RAW_DIR / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
