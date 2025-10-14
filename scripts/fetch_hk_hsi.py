"""Placeholder fetcher for Hong Kong Hang Seng family indices."""

from __future__ import annotations

import json

from .common import ensure_data_dir, load_indices


def main() -> None:
    indices = [entry for entry in load_indices() if entry.get("class") == "HK_HSI"]
    output_dir = ensure_data_dir("raw", "hk_hsi")
    summary_path = output_dir / "indices_config.json"

    summary_payload = [
        {
            "name": idx["name"],
            "code": idx["code"],
            "factsheet_url": idx.get("factsheet_url"),
        }
        for idx in indices
    ]
    summary_path.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if not (output_dir / "README.stub").exists():
        (output_dir / "README.stub").write_text(
            "TODO: download Hang Seng factsheets and parse valuation metrics.\n",
            encoding="utf-8",
        )

    print(f"Prepared {len(indices)} Hang Seng index entries in {output_dir}")


if __name__ == "__main__":
    main()
