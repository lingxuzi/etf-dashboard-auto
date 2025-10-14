"""Placeholder fetcher for mainland CSI indices."""

from __future__ import annotations

import json
from pathlib import Path

from .common import ensure_data_dir, load_indices


def main() -> None:
    indices = [entry for entry in load_indices() if entry.get("class") == "CN_CSI"]
    output_dir = ensure_data_dir("raw", "cn_csi")
    marker_path = output_dir / "README.stub"

    if not marker_path.exists():
        marker_path.write_text(
            "TODO: implement AKShare pull for CSI indices.\n",
            encoding="utf-8",
        )

    summary_path = output_dir / "indices_config.json"
    summary_payload = [{"name": idx["name"], "code": idx["code"]} for idx in indices]
    summary_path.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Prepared {len(indices)} CSI index entries in {output_dir}")


if __name__ == "__main__":
    main()
