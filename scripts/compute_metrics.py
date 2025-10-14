"""Aggregate raw data to compute percentiles & drawdowns."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from .common import DATA_ROOT, ensure_data_dir, load_indices


PROCESSED_DIR = ensure_data_dir("processed")
RAW_CN = DATA_ROOT / "raw" / "cn_csi"
RAW_HK = DATA_ROOT / "raw" / "hk_hsi"
RAW_US = DATA_ROOT / "raw" / "us_index"


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, parse_dates=["date"])


def _ten_year_window(series: pd.Series) -> pd.Series:
    if series.empty:
        return series
    last_date = series.index.max()
    cutoff = last_date - pd.DateOffset(years=10)
    window = series[series.index >= cutoff]
    return window if not window.empty else series


def _percentile(series: pd.Series) -> Optional[float]:
    series = series.dropna()
    if series.empty:
        return None
    series = series.sort_index()
    window = _ten_year_window(series)
    current = window.iloc[-1]
    percentile = (window <= current).sum() / len(window) * 100.0
    return float(np.clip(percentile, 0.0, 100.0))


def _current_value(series: pd.Series) -> Optional[float]:
    series = series.dropna()
    if series.empty:
        return None
    series = series.sort_index()
    return float(series.iloc[-1])


def _compute_drawdown(prices: pd.Series) -> Optional[float]:
    prices = prices.dropna()
    if prices.empty:
        return None
    prices = prices.sort_index()
    window = _ten_year_window(prices)
    rolling_max = window.cummax()
    drawdown_series = 1.0 - window / rolling_max
    value = drawdown_series.iloc[-1]
    return float(np.clip(value, 0.0, 1.0))


def _load_series(cfg: dict[str, object]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    code = cfg["code"]
    market = cfg.get("class")
    if market == "CN_CSI":
        base = RAW_CN
    elif market == "HK_HSI":
        base = RAW_HK
    elif market == "US_INDEX":
        base = RAW_US
    else:
        raise ValueError(f"未知分类: {market}")

    valuation = _read_csv(base / f"{code}_valuation.csv")
    price = _read_csv(base / f"{code}_price.csv")
    dividend_extra = _read_csv(base / f"{code}_dividend.csv")
    return valuation, price, dividend_extra


def main() -> None:
    indices = load_indices()
    records: list[dict[str, object]] = []

    for cfg in indices:
        code = cfg["code"]
        valuation_df, price_df, dividend_df = _load_series(cfg)

        if not valuation_df.empty and "date" in valuation_df.columns:
            valuation_df = valuation_df.sort_values("date")
            valuation_df.set_index("date", inplace=True, drop=False)
        else:
            valuation_df = pd.DataFrame(columns=["date", "pe", "pb", "dividend_yield"])
        if not price_df.empty and "date" in price_df.columns:
            price_df = price_df.sort_values("date")
            price_df.set_index("date", inplace=True, drop=False)
        else:
            price_df = pd.DataFrame(columns=["date", "close"])
        if not dividend_df.empty and "date" in dividend_df.columns:
            dividend_df = dividend_df.sort_values("date")
            dividend_df.set_index("date", inplace=True, drop=False)
        else:
            dividend_df = pd.DataFrame(columns=["date", "dividend_yield"])

        pe_pct = _percentile(valuation_df.get("pe", pd.Series(dtype=float)))
        pb_pct = _percentile(valuation_df.get("pb", pd.Series(dtype=float)))

        if "dividend_yield" in valuation_df.columns and not valuation_df.empty:
            div_series = valuation_df["dividend_yield"]
        else:
            div_series = dividend_df.get("dividend_yield", pd.Series(dtype=float))
        div_pct = _percentile(div_series)

        drawdown = _compute_drawdown(price_df.get("close", pd.Series(dtype=float)))

        records.append(
            {
                "index_code": code,
                "pe_pct": pe_pct,
                "pb_pct": pb_pct,
                "div_yield_pct": div_pct,
                "drawdown": drawdown,
                "pe_current": _current_value(valuation_df.get("pe", pd.Series(dtype=float))),
                "pb_current": _current_value(valuation_df.get("pb", pd.Series(dtype=float))),
                "dividend_current": _current_value(div_series),
            }
        )

    metrics_df = pd.DataFrame(records)
    metrics_path = PROCESSED_DIR / "metrics.csv"
    metrics_df.to_csv(metrics_path, index=False)
    print(f"已生成指标文件: {metrics_path} ({len(metrics_df)} 条记录)")


if __name__ == "__main__":
    main()
