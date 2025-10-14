"""Fetch CSI index valuation & price series via AKShare."""

from __future__ import annotations

import datetime as dt
import json
from typing import Iterable

import pandas as pd

try:
    import akshare as ak
except ImportError as exc:  # pragma: no cover - handled at runtime
    raise SystemExit(
        "akshare 未安装，无法抓取中证指数数据。请先运行 `pip install -r requirements.txt`"
    ) from exc

from .common import ensure_data_dir, load_indices


RAW_DIR = ensure_data_dir("raw", "cn_csi")
VAL_FILENAME = "{code}_valuation.csv"
PRICE_FILENAME = "{code}_price.csv"


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename AKShare 返回的中文字段，提取通用指标。"""

    rename_map = {
        "日期": "date",
        "date": "date",
        "trade_date": "date",
        "收盘": "close",
        "close": "close",
        "市盈率": "pe",
        "市盈率1": "pe",
        "市盈率2": "pe_secondary",
        "pe_ttm": "pe",
        "市净率": "pb",
        "市净率1": "pb",
        "市净率2": "pb_secondary",
        "pb_mrq": "pb",
        "股息率": "dividend_yield",
        "股息率1": "dividend_yield",
        "股息率2": "dividend_yield_secondary",
    }
    df = df.rename(columns={raw: rename_map.get(raw, raw) for raw in df.columns})
    return df


def _select_first_valid(df: pd.DataFrame, candidates: Iterable[str]) -> pd.Series:
    for key in candidates:
        if key in df.columns:
            series = pd.to_numeric(df[key], errors="coerce")
            if series.notna().any():
                return series
    return pd.Series(dtype="float64")


def fetch_valuation(symbol: str) -> pd.DataFrame:
    raw = ak.stock_zh_index_value_csindex(symbol=symbol)
    if raw is None or len(raw) == 0:
        raise RuntimeError(f"akshare 返回空数据: {symbol}")
    df = _normalize_columns(raw)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date")

    pe = _select_first_valid(df, ["pe", "pe_secondary"])
    pb = _select_first_valid(df, ["pb", "pb_secondary"])
    dividend = _select_first_valid(df, ["dividend_yield", "dividend_yield_secondary"])

    valuation = pd.DataFrame({
        "date": df["date"],
        "pe": pe.reindex(df.index),
        "pb": pb.reindex(df.index),
        "dividend_yield": dividend.reindex(df.index),
    }).dropna(how="all", subset=["pe", "pb", "dividend_yield"])
    valuation = valuation.drop_duplicates(subset=["date"]).sort_values("date")

    return valuation


def _candidate_symbols(symbol: str) -> list[str]:
    base = symbol.lower()
    if ":" in base:
        _, code = base.split(":", 1)
    else:
        code = base
    code = code.replace("sh", "").replace("sz", "")
    candidates = [symbol, base, code]
    if not code.startswith("sh"):
        candidates.extend([f"sh{code}", f"sz{code}"])
    return list(dict.fromkeys(candidates))  # 去重复保持顺序


def fetch_price(symbol: str, start: dt.date) -> pd.DataFrame:
    last_error: Exception | None = None
    for candidate in _candidate_symbols(symbol):
        try:
            raw = ak.stock_zh_index_daily_em(symbol=candidate, start_date=start.strftime("%Y%m%d"))
            df = _normalize_columns(raw)
            if df.empty:
                continue
            if "date" not in df.columns:
                df["date"] = pd.to_datetime(df.index)
            else:
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df.dropna(subset=["date"]).sort_values("date")
            close = _select_first_valid(df, ["close", "收盘", "close_price"])
            price = pd.DataFrame({
                "date": df["date"],
                "close": close.reindex(df.index),
            }).dropna(subset=["close"])
            price = price.drop_duplicates(subset=["date"]).sort_values("date")
            if not price.empty:
                return price
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue

    if last_error:
        raise last_error
    raise RuntimeError(f"未能获取指数行情: {symbol}")


def main() -> None:
    indices = [entry for entry in load_indices() if entry.get("class") == "CN_CSI"]
    start_date = dt.date.today() - dt.timedelta(days=365 * 15)
    summary = []

    for cfg in indices:
        code = cfg["code"]
        price_symbol = cfg.get("price_symbol") or code

        try:
            valuation_df = fetch_valuation(code)
            valuation_path = RAW_DIR / VAL_FILENAME.format(code=code)
            valuation_df.to_csv(valuation_path, index=False)

            price_df = fetch_price(price_symbol, start_date)
            price_path = RAW_DIR / PRICE_FILENAME.format(code=code)
            price_df.to_csv(price_path, index=False)

            summary.append({
                "code": code,
                "valuation_rows": int(len(valuation_df)),
                "price_rows": int(len(price_df)),
            })
            print(f"[CN_CSI] {code} -> {len(valuation_df)} 估值, {len(price_df)} 行情")
        except Exception as exc:
            failure_path = RAW_DIR / f"{code}_error.log"
            failure_path.write_text(str(exc), encoding="utf-8")
            print(f"[CN_CSI] {code} 抓取失败: {exc}")

    (RAW_DIR / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
