"""Placeholder fetcher for US indices via Yahoo Finance."""

from __future__ import annotations

import json

from .common import ensure_data_dir, load_indices


def main() -> None:
    indices = [entry for entry in load_indices() if entry.get("class") == "US_INDEX"]
    output_dir = ensure_data_dir("raw", "us_index")
    summary_path = output_dir / "indices_config.json"

    summary_payload = [
        {
            "name": idx["name"],
            "code": idx["code"],
            "price_symbol": idx.get("price_symbol"),
            "etf_proxies": idx.get("etf_proxies", []),
        }
        for idx in indices
    ]
    summary_path.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if not (output_dir / "README.stub").exists():
        (output_dir / "README.stub").write_text(
            "TODO: fetch Yahoo Finance history and ETF dividend series.\n",
            encoding="utf-8",
        )

    print(f"Prepared {len(indices)} US index entries in {output_dir}")


if __name__ == "__main__":
    main()
