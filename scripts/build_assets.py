"""Transform processed metrics into the dashboard CSV."""

from __future__ import annotations

from pathlib import Path
from shutil import copyfile

from .common import DATA_ROOT, PROJECT_ROOT


def main() -> None:
    processed_dir = DATA_ROOT / "processed"
    docs_dir = PROJECT_ROOT / "docs"
    target_csv = docs_dir / "assets.csv"
    sample_csv = docs_dir / "assets.sample.csv"

    if not processed_dir.exists():
        processed_dir.mkdir(parents=True, exist_ok=True)

    if sample_csv.exists() and not processed_dir.joinpath("assets.generated").exists():
        # 临时策略：在真实算法完成前使用示例数据占位，避免仪表盘断档。
        copyfile(sample_csv, target_csv)
        processed_dir.joinpath("assets.generated").write_text(
            "placeholder\n",
            encoding="utf-8",
        )
        print(f"Copied sample assets to {target_csv}")
    else:
        print(f"No action taken; expecting future implementation to write {target_csv}")


if __name__ == "__main__":
    main()
