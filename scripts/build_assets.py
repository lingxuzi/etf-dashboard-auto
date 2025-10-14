"""Transform processed metrics into the dashboard CSV."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .common import DATA_ROOT, PROJECT_ROOT, load_indices


def _safe_percent(value, default: float) -> float:
    if value is None or pd.isna(value):
        return float(default)
    return float(round(float(value), 2))


def _safe_drawdown(value) -> float:
    if value is None or pd.isna(value):
        return 0.0
    return float(round(float(value), 4))


def _format_etfs(cfg: dict[str, object]) -> str:
    display = cfg.get("etf_display")
    if isinstance(display, list) and display:
        return "; ".join(display)
    proxies = cfg.get("etf_proxies") or []
    if isinstance(proxies, list):
        return "; ".join(str(p) for p in proxies)
    return ""


def main() -> None:
    metrics_path = DATA_ROOT / "processed" / "metrics.csv"
    docs_dir = PROJECT_ROOT / "docs"
    target_csv = docs_dir / "assets.csv"

    if not metrics_path.exists():
        raise SystemExit(f"缺少指标文件: {metrics_path}，请先运行抓数与计算脚本")

    metrics_df = pd.read_csv(metrics_path)
    metrics_df.set_index("index_code", inplace=True)

    rows = []
    for cfg in load_indices():
        code = cfg["code"]
        metrics = metrics_df.loc[code] if code in metrics_df.index else {}
        rows.append(
            {
                "index_name": cfg["name"],
                "index_code": code,
                "etfs": _format_etfs(cfg),
                "pe_pct": _safe_percent(metrics.get("pe_pct"), 100.0),
                "pb_pct": _safe_percent(metrics.get("pb_pct"), 100.0),
                "div_yield_pct": _safe_percent(metrics.get("div_yield_pct"), 0.0),
                "drawdown": _safe_drawdown(metrics.get("drawdown")),
            }
        )

    assets_df = pd.DataFrame(rows)
    assets_df.to_csv(target_csv, index=False)
    print(f"仪表盘数据已写入 {target_csv} ({len(assets_df)} 条记录)")


if __name__ == "__main__":
    main()
