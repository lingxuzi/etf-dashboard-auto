"""Fetch Hang Seng index fundamentals via factsheets & Yahoo Finance."""

from __future__ import annotations

import datetime as dt
import io
import json
import re
from typing import Iterable

import pandas as pd
import requests
import yfinance as yf

try:
    import pdfplumber
except ImportError as exc:  # pragma: no cover - fail loudly
    raise SystemExit(
        "缺少 pdfplumber 库，无法解析恒生指数月度事实卡。请先 `pip install -r requirements.txt`"
    ) from exc

from .common import ensure_data_dir, load_indices


RAW_DIR = ensure_data_dir("raw", "hk_hsi")
VAL_FILENAME = "{code}_valuation.csv"
PRICE_FILENAME = "{code}_price.csv"


def _candidate_symbols(cfg: dict[str, object]) -> list[str]:
    candidates: list[str] = []
    primary = cfg.get("price_symbol")
    if isinstance(primary, str) and primary:
        candidates.append(primary)
    proxies = cfg.get("etf_proxies") or []
    if isinstance(proxies, Iterable):
        for ticker in proxies:
            if isinstance(ticker, str):
                candidates.append(ticker)
    return list(dict.fromkeys(candidates))


def _download_pdf(url: str) -> bytes:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.content


def _parse_factsheet(pdf_bytes: bytes) -> dict[str, float | None]:
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        lines: list[str] = []
        for page in pdf.pages:
            text = page.extract_text() or ""
            lines.extend(text.splitlines())

    def extract_value(keys: Iterable[str]) -> float | None:
        pattern = re.compile(r"(-?\d+(?:\.\d+)?)")
        for line in lines:
            line_norm = line.replace("：", ":").lower()
            if any(key in line_norm for key in keys):
                match = pattern.search(line)
                if match:
                    value = float(match.group(1))
                    if "%" in line:
                        return value / 100.0
                    return value
        return None

    return {
        "pe": extract_value(["p/e", "pe ratio", "市盈率"]),
        "pb": extract_value(["p/b", "pb ratio", "市净率"]),
        "dividend_yield": extract_value(["dividend yield", "股息率"]),
    }


def _append_timeseries(path, data: pd.DataFrame) -> None:
    if path.exists():
        existing = pd.read_csv(path, parse_dates=["date"])
    else:
        existing = pd.DataFrame(columns=data.columns)
    merged = pd.concat([existing, data], ignore_index=True)
    merged = merged.drop_duplicates(subset=["date"], keep="last").sort_values("date")
    merged.to_csv(path, index=False)


def fetch_price_series(candidates: list[str], start: dt.date) -> pd.DataFrame:
    last_error: Exception | None = None
    for ticker in candidates:
        try:
            df = yf.download(ticker, start=start.isoformat(), progress=False, auto_adjust=False)
            if df.empty:
                continue
            closes = df.reset_index()[["Date", "Close"]]
            closes.columns = ["date", "close"]
            closes["date"] = pd.to_datetime(closes["date"])
            closes = closes.dropna(subset=["date", "close"]).sort_values("date")
            if not closes.empty:
                return closes
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue
    if last_error:
        raise last_error
    raise RuntimeError("未能获取任何有效的行情数据")


def main() -> None:
    indices = [entry for entry in load_indices() if entry.get("class") == "HK_HSI"]
    start_date = dt.date.today() - dt.timedelta(days=365 * 15)
    summary: list[dict[str, object]] = []

    for cfg in indices:
        code = cfg["code"]
        factsheet_url = cfg.get("factsheet_url")
        candidates = _candidate_symbols(cfg)

        try:
            if not factsheet_url:
                raise ValueError("缺少 factsheet_url")
            pdf_bytes = _download_pdf(factsheet_url)
            info = _parse_factsheet(pdf_bytes)
            metrics_date = dt.date.today().replace(day=1)
            valuation_df = pd.DataFrame(
                {
                    "date": [pd.to_datetime(metrics_date)],
                    "pe": [info.get("pe")],
                    "pb": [info.get("pb")],
                    "dividend_yield": [info.get("dividend_yield")],
                }
            )
            _append_timeseries(RAW_DIR / VAL_FILENAME.format(code=code), valuation_df)

            price_df = fetch_price_series(candidates, start_date)
            price_path = RAW_DIR / PRICE_FILENAME.format(code=code)
            price_df.to_csv(price_path, index=False)

            summary.append(
                {
                    "code": code,
                    "valuation_records": int(len(valuation_df)),
                    "price_rows": int(len(price_df)),
                }
            )
            print(f"[HK_HSI] {code} -> 估值更新, 行情 {len(price_df)} 行")
        except Exception as exc:  # noqa: BLE001
            error_path = RAW_DIR / f"{code}_error.log"
            error_path.write_text(str(exc), encoding="utf-8")
            print(f"[HK_HSI] {code} 抓取失败: {exc}")

    (RAW_DIR / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
