"""Aggregate raw metric inputs and compute percentile statistics."""

from __future__ import annotations

from pathlib import Path

from .common import DATA_ROOT, ensure_data_dir


def main() -> None:
    metrics_dir = ensure_data_dir("processed")
    placeholder = metrics_dir / "README.stub"
    if not placeholder.exists():
        placeholder.write_text(
            "TODO: synthesize metrics from raw fetch outputs.\n",
            encoding="utf-8",
        )

    print(f"Metrics placeholder ready at {metrics_dir}")


if __name__ == "__main__":
    main()
